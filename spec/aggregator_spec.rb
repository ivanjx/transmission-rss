require 'spec_helper'

describe Aggregator do
  SEEN_FILE = tmp_path(:seen_file)
  FEEDS = [
    Feed.new('https://www.archlinux.org/feeds/releases/')
  ]

  subject do
    Aggregator.new(FEEDS, seen_file: SEEN_FILE)
  end

  after(:all) do
    FileUtils.rm_f(SEEN_FILE)
  end

  describe '#fetch' do
    it 'returns content' do
      VCR.use_cassette('feed_fetch', MATCH_REQUESTS_ON) do
        content = subject.send(:fetch, FEEDS.first)

        expect(content).not_to be_empty
        expect(content.size).to eq(1725)
      end
    end
  end

  describe '#parse' do
    it 'returns content' do
      VCR.use_cassette('feed_fetch', MATCH_REQUESTS_ON) do
        content = subject.send(:parse, subject.send(:fetch, FEEDS.first))

        expect(content.size).to eq(3)

        description_matches = content
          .map(&:title)
          .map { |x| x =~ /^[0-9]{4}\.[0-9]{2}\.[0-9]{2}/ }
          .uniq

        expect(description_matches).to eq([0])

        urls = content.map(&:enclosure).map(&:url)

        urls.each do |url|
          url = URI.parse(url)

          expect(url.scheme).to eq('https')
          expect(url.host).to eq('www.archlinux.org')
          expect(File.basename(url.path)).to match(/\.iso\.torrent$/)
        end
      end
    end
  end

  describe '#process_link' do
    before(:each) do    
      VCR.use_cassette('feed_fetch', MATCH_REQUESTS_ON) do  
        @item = subject.send(:parse, subject.send(:fetch, FEEDS.first)).first
        subject.seen.clear!
      end
    end

    it 'returns enclosure url and adds url to seen' do
      content = subject.send(:process_link, FEEDS.first, @item)

      url = URI.parse(content)

      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      expect(File.basename(url.path)).to match(/\.iso\.torrent$/)
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.enclosure.url)).to be true
    end

    it 'returns link and adds link to seen if no enclosure url' do
      @item.enclosure = nil
      
      content = subject.send(:process_link, FEEDS.first, @item)

      url = URI.parse(content)
      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      expect(File.basename(url.path)).to match(/2020\.01\.01$/)
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.link)).to be true
    end

    it 'returns nil if no link or enclosure url' do
      @item.enclosure = nil
      @item.link = nil
      
      content = subject.send(:process_link, FEEDS.first, @item)

      expect(content).to be_nil
      
      expect(subject.seen.size).to eq(0)
    end

    it 'returns nil but adds url to seen if unseen but no regexp match' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'regexp' => 'WILL_NOT_MATCH$'
      }) 
      
      content = subject.send(:process_link, feed, @item)
      
      expect(content).to be_nil

      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.enclosure.url)).to be true
    end    

    it 'returns enclosure url and adds guid to seen if seen_by_guid' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'seen_by_guid' => true
      })

      content = subject.send(:process_link, feed, @item)

      url = URI.parse(content)
      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      expect(File.basename(url.path)).to match(/\.iso\.torrent$/)
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.guid.content.to_s)).to be true
    end
    
    it 'returns link and adds guid to seen if seen_by_guid but no enclosure url' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'seen_by_guid' => true
      }) 
      @item.enclosure = nil
      
      content = subject.send(:process_link, feed, @item)

      url = URI.parse(content)
      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      expect(File.basename(url.path)).to match(/2020\.01\.01$/)
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.guid.content.to_s)).to be true
    end

    it 'returns enclosure url and adds url to seen if seen_by_guid but no guid' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'seen_by_guid' => true
      })
      @item.guid = nil

      content = subject.send(:process_link, feed, @item)
      
      expect(content).not_to be_empty
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.enclosure.url)).to be true
    end

    it 'returns link and adds link to seen if seen_by_guid but no guid' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'seen_by_guid' => true
      })
      @item.enclosure = nil
      @item.guid = nil

      content = subject.send(:process_link, feed, @item)
      
      expect(content).not_to be_empty
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.link)).to be true
    end

    it 'returns enclosure url and adds guid to seen if seen_by_guid but guid has no attributes' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'seen_by_guid' => true
      })
      @item.guid = @item.guid.content

      content = subject.send(:process_link, feed, @item)
      
      expect(content).not_to be_empty
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.guid)).to be true
    end

    it 'returns link and adds guid to seen if seen_by_guid but no enclosure link and guid has no attributes' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'seen_by_guid' => true
      })
      @item.enclosure = nil
      @item.guid = @item.guid.content

      content = subject.send(:process_link, feed, @item)
      
      expect(content).not_to be_empty
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.guid)).to be true
    end
    
    it 'returns nil but adds to seen if seen_by_guid and unseen but no regexp match' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'regexp' => 'WILL_NOT_MATCH$',
        'seen_by_guid' => true
      }) 
      
      content = subject.send(:process_link, feed, @item)
      
      expect(content).to be_nil

      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.guid.content)).to be true
    end

    it 'calls on_new_item when returning link and adding to seen' do
      on_new_item_args = nil
      subject.on_new_item do | arg1, arg2, arg3 |
        on_new_item_args = Hash[binding.local_variables.map{|x| [x, binding.local_variable_get(x)]}]
      end

      content = subject.send(:process_link, FEEDS.first, @item)

      expect(on_new_item_args).not_to be_nil
      expect(on_new_item_args[:arg1]).to eq(@item.enclosure.url)
      expect(on_new_item_args[:arg2]).to be(FEEDS.first)
      expect(on_new_item_args[:arg3]).to be_nil
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.enclosure.url)).to be true
    end

    it 'calls on_new_item with download_path when download_path set on feed' do
      on_new_item_args = nil
      subject.on_new_item do | arg1, arg2, arg3 |
        on_new_item_args = Hash[binding.local_variables.map{|x| [x, binding.local_variable_get(x)]}]
      end
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'download_path' => '/tmp'
      })

      content = subject.send(:process_link, feed, @item)

      expect(on_new_item_args).not_to be_nil
      expect(on_new_item_args[:arg1]).to eq(@item.enclosure.url)
      expect(on_new_item_args[:arg2]).to be(feed)
      expect(on_new_item_args[:arg3]).to eq('/tmp')
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.enclosure.url)).to be true
    end
    
    it 'calls on_new_item with download_path from regexp when matching' do
      on_new_item_args = nil
      subject.on_new_item do | arg1, arg2, arg3 |
        on_new_item_args = Hash[binding.local_variables.map{|x| [x, binding.local_variable_get(x)]}]
      end
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'regexp' => [{'matcher' => '.+', 'download_path' => '/tmp/foo'}]
      })

      content = subject.send(:process_link, feed, @item)

      expect(on_new_item_args).not_to be_nil
      expect(on_new_item_args[:arg1]).to eq(@item.enclosure.url)
      expect(on_new_item_args[:arg2]).to be(feed)
      expect(on_new_item_args[:arg3]).to eq('/tmp/foo')
      
      expect(subject.seen.size).to eq(1)
      expect(subject.seen.include?(@item.enclosure.url)).to be true
    end

    [Client::Unauthorized, Errno::ECONNREFUSED, Timeout::Error].each { | err |
      it "does not add to seen when on_new_item throws #{err}" do
        subject.on_new_item do
          raise err.new "Test #{err}"
        end
  
        content = subject.send(:process_link, FEEDS.first, @item)
  
        expect(subject.seen.size).to eq(0)
      end
    }
  end

  describe '#process_link with field_name' do
    before(:each) do    
      VCR.use_cassette('feed_fetch', MATCH_REQUESTS_ON) do  
        @item = subject.send(:parse, subject.send(:fetch, FEEDS.first)).first
        subject.seen.clear!
      end
    end

    it 'uses custom field when field_name is set to custom field' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'field_name' => 'customField'
      })
      
      # Mock the item to have a custom field
      allow(@item).to receive(:respond_to?).with(:customField).and_return(true)
      allow(@item).to receive(:customField).and_return('http://custom.url/torrent.torrent')
      
      content = subject.send(:process_link, feed, @item)
      
      expect(content).to eq('http://custom.url/torrent.torrent')
      
      expect(subject.seen.size).to eq(1)
    end

    it 'falls back to regular link when custom field is not found' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'field_name' => 'nonexistentField'
      })
      
      # Mock the item to not have the custom field
      allow(@item).to receive(:respond_to?).with(:nonexistentField).and_return(false)
      
      content = subject.send(:process_link, feed, @item)
      
      url = URI.parse(content)
      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      
      expect(subject.seen.size).to eq(1)
    end

    it 'uses custom field infoHash when field_name is set to infoHash' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'field_name' => 'infoHash'
      })
      
      # Mock the item to have an infoHash field
      allow(@item).to receive(:respond_to?).with(:infoHash).and_return(true)
      allow(@item).to receive(:infoHash).and_return('magnet:?xt=urn:btih:ad9d77d8c9aca5432cac4782e0419aec634e97be')
      
      content = subject.send(:process_link, feed, @item)
      
      expect(content).to eq('magnet:?xt=urn:btih:ad9d77d8c9aca5432cac4782e0419aec634e97be')
      
      expect(subject.seen.size).to eq(1)
    end

    it 'falls back to regular link when infoHash field is not found' do
      feed = Feed.new({
        'url' => FEEDS.first.url,
        'field_name' => 'infoHash'
      })
      
      # Mock the item to not have the infoHash field
      allow(@item).to receive(:respond_to?).with(:infoHash).and_return(false)
      
      content = subject.send(:process_link, feed, @item)
      
      url = URI.parse(content)
      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      
      expect(subject.seen.size).to eq(1)
    end

    it 'uses regular link when field_name is not specified' do
      feed = Feed.new({
        'url' => FEEDS.first.url
      })
      
      content = subject.send(:process_link, feed, @item)
      
      url = URI.parse(content)
      expect(url.scheme).to eq('https')
      expect(url.host).to eq('www.archlinux.org')
      
      expect(subject.seen.size).to eq(1)
    end
  end
end
