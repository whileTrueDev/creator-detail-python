from collectors.collector import Collector

if __name__ == '__main__':
    collector = Collector()
    collector.process()

    # afreeca platform 사용
    collector.set_platform('afreeca')
    collector.process()
