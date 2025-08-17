import logging
import sys
from aggregator import Aggregator

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'transmission-rss.conf.example'
    agg = Aggregator(config_path)
    agg.run()
