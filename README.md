transmission-rss
================

This tool monitors RSS feeds and automatically adds torrent or magnet links to a Transmission server using its RPC API.

It works with transmission-daemon and transmission-gtk (if the web frontend is enabled). Sites like showrss.karmorra.info, nyaa.si, and others are supported as feed sources.

Installation
------------

### From source

```sh
git clone https://github.com/ivanjx/transmission-rss
cd transmission-rss
python -m venv .venv
.venv\Scripts\Activate.ps1  # On Windows
source .venv/bin/activate   # On Linux/macOS
pip install -r requirements.txt
```

### Via Docker

```sh
docker build -t transmission-rss .
docker run -t -v $(pwd)/transmission-rss.conf.example:/app/transmission-rss.conf transmission-rss
```


Configuration
-------------

A YAML formatted config file is expected (see `transmission-rss.conf.example`).
Only options implemented in the Python version are supported:


### Minimal example

```yaml
feeds:
  - url: http://example.com/feed1
  - url: http://example.com/feed2
```

Feed item titles can be filtered by a regular expression:

```yaml
feeds:
  - url: http://example.com/feed1
    regexp: foo
  - url: http://example.com/feed2
    regexp: (foo|bar)
```

Feeds can also be configured to download files to a specific directory:

```yaml
feeds:
  - url: http://example.com/feed1
    download_path: /home/user/Downloads
```

### Supported options

See `transmission-rss.conf.example` for a full list of supported options.


Usage
-----

To run the Python version:

```sh
python src/transmission_rss.py transmission-rss.conf.example
```

Or with Docker:

```sh
docker run -t -v $(pwd)/transmission-rss.conf.example:/app/transmission-rss.conf transmission-rss
```
