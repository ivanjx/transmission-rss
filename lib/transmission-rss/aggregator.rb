require 'open-uri'
require 'open_uri_redirections'
require 'rss'
require 'openssl'
require 'uri'

libdir = File.dirname(__FILE__)
require File.join(libdir, 'log')
require File.join(libdir, 'callback')

module TransmissionRSS
  # Class for aggregating torrent files through RSS feeds.
  class Aggregator
    extend Callback
    callback(:on_new_item) # Declare callback for new items.

    attr_reader :seen

    def initialize(feeds = [], options = {})
      reinitialize!(feeds, options)
    end

    def reinitialize!(feeds = [], options = {})
      seen_file = options[:seen_file]

      # Prepare Array of feeds URLs.
      @feeds = feeds.map { |config| TransmissionRSS::Feed.new(config) }

      # Nothing seen, yet.
      @seen = SeenFile.new(seen_file)

      # Initialize log instance.
      @log = Log.instance

      # Log number of +@seen+ URIs.
      @log.debug(@seen.size.to_s + ' uris from seenfile')
    end

    # Get file enclosures from all feeds items and call on_new_item callback
    # with torrent file URL as argument.
    def run(interval = 600)
      @log.debug('aggregator start')

      loop do
        @feeds.each do |feed|
          @log.debug('aggregate ' + feed.url)

          begin
            content = fetch(feed)
          rescue StandardError => e
            @log.debug("retrieval error (#{e.class}: #{e.message})")
            next
          end

          # gzip HTTP Content-Encoding is not automatically decompressed in
          # Ruby 1.9.3.
          content = decompress(content) if RUBY_VERSION == '1.9.3'
          begin
            items = parse(content)
          rescue StandardError => e
            @log.debug("parse error (#{e.class}: #{e.message})")
            next
          end

          items.each do |item|
            result = process_link(feed, item)
            next if result.nil?
          end
        end

        if interval == -1
          @log.debug('single run mode, exiting')
          break
        end

        sleep(interval)
      end
    end

    private

    def fetch(feed)
      options = {
        allow_redirections: :safe,
        'User-Agent' => 'transmission-rss'
      }

      unless feed.validate_cert
        @log.debug('aggregate certificate validation: false')
        options[:ssl_verify_mode] = OpenSSL::SSL::VERIFY_NONE
      end

      # open for URIs is obsolete, URI.open does not work in 2.4
      URI.send(:open, feed.url, options).read
    end

    def parse(content)
      RSS::Parser.parse(content, false).items
    end

    def decompress(string)
      Zlib::GzipReader.new(StringIO.new(string)).read
    rescue Zlib::GzipFile::Error, Zlib::Error
      string
    end

    def process_link(feed, item)
      link = item.enclosure.url rescue item.link

      # Item contains no link.
      return if link.nil?

      # Link is not a String directly.
      link = link.href if link.class != String

      # Try to extract torrent hash from RSS item and create magnet link if available
      torrent_hash = nil
      if feed.use_hash
        torrent_hash = extract_torrent_hash(item)
        if torrent_hash
          link = create_magnet_link(torrent_hash, item.title)
        end
      end

      # Determine whether to use guid or link as seen hash
      seen_value = feed.seen_by_guid ? (item.guid.content rescue item.guid || link).to_s : link

      # The link is not in +@seen+ Array.
      unless @seen.include?(seen_value)
        # Skip if filter defined and not matching.
        unless feed.matches_regexp?(item.title) && !feed.exclude?(item.title)
          @seen.add(seen_value)
          return
        end

        @log.debug('on_new_item event ' + link)

        download_path = feed.download_path(item.title)

        begin
          if feed.delay_time > 0
            @log.debug("sleeping for #{feed.delay_time} seconds...")
            sleep(feed.delay_time)
          end
          on_new_item(link, feed, download_path)
        rescue Client::TooManyRequests
          @log.debug('TooManyRequests: Consider adding delay_time to this feed.')
        rescue Client::Unauthorized, Errno::ECONNREFUSED, Timeout::Error
          @log.debug('not added to seen file ' + link)
        else
          @seen.add(seen_value)
        end
      end

      return link
    end

    # Extract torrent hash from RSS item
    # Supports various RSS feed formats that include torrent hashes
    def extract_torrent_hash(item)
      # Try to access namespaced elements for torrent hash
      # Common patterns: nyaa:infoHash, torrent:infoHash, etc.
      
      # First, try direct method calls for common namespaced elements
      hash_candidates = []
      
      # Try various method names that might contain the hash
      potential_methods = [
        'infoHash', 'info_hash', 'hash', 'torrent_hash',
        'nyaa_infoHash', 'nyaa_info_hash'
      ]
      
      potential_methods.each do |method_name|
        ['', 'nyaa_', 'torrent_'].each do |prefix|
          full_method = (prefix + method_name).to_sym
          begin
            if item.respond_to?(full_method)
              value = item.send(full_method)
              hash_candidates << extract_hash_from_value(value)
            end
          rescue
            # Ignore method call errors
          end
        end
      end

      # Try to access through item's instance variables
      item.instance_variables.each do |var|
        begin
          value = item.instance_variable_get(var)
          hash_candidates << extract_hash_from_value(value)
        rescue
          # Ignore access errors
        end
      end

      # Try to extract from item content/description using regex
      content_sources = []
      begin
        content_sources << item.description.content if item.description.respond_to?(:content)
      rescue; end
      
      begin
        content_sources << item.description.to_s if item.description
      rescue; end
      
      begin
        content_sources << item.content.content if item.content.respond_to?(:content)
      rescue; end
      
      begin
        content_sources << item.content.to_s if item.content
      rescue; end

      content_sources.each do |content|
        next unless content.is_a?(String)
        hash_candidates << extract_hash_from_string(content)
      end

      # Try accessing through the raw XML if available
      begin
        if item.respond_to?(:source) && item.source
          hash_candidates << extract_hash_from_string(item.source.to_s)
        end
      rescue; end

      # Return the first valid hash found
      hash_candidates.compact.first
    end

    # Extract hash from a value (string, object, etc.)
    def extract_hash_from_value(value)
      return nil unless value
      
      if value.is_a?(String)
        return extract_hash_from_string(value)
      elsif value.respond_to?(:content)
        return extract_hash_from_string(value.content.to_s)
      elsif value.respond_to?(:to_s)
        return extract_hash_from_string(value.to_s)
      end
      
      nil
    end

    # Extract SHA-1 hash from string content
    def extract_hash_from_string(content)
      return nil unless content.is_a?(String)
      
      # Look for SHA-1 hash patterns (40 hex characters)
      hash_match = content.match(/\b([a-fA-F0-9]{40})\b/i)
      if hash_match
        return hash_match[1].downcase
      end
      
      nil
    end

    # Create a magnet link from torrent hash and title
    def create_magnet_link(hash, title)
      # Encode title for URL
      encoded_title = URI.encode_www_form_component(title || "")
      
      # Create basic magnet link with hash and display name
      magnet_link = "magnet:?xt=urn:btih:#{hash}"
      magnet_link += "&dn=#{encoded_title}" unless encoded_title.empty?
      
      magnet_link
    end
  end
end
