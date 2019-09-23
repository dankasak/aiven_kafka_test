import argparse , json

from linux_metrics import cpu_stat
from kafka import KafkaProducer

parser = argparse.ArgumentParser()

parser.add_argument( "--sampleInterval"          , help = "number of seconds between each sample"   , default = 2                               , type = int  )

parser.add_argument( "--kafkaEndpoint"           , help = "the endpoint of the kafka service"       , default = "kafka-bd35e9a-project-ffc3.aivencloud.com:24744" )
parser.add_argument( "--kafkaAccessKey"         , help = "the path to the kafka access key"         , default = "kafka_access_key" )
parser.add_argument( "--kafkaAccessCertificate" , help = "the path to the kafka access certificate" , default = "kafka_access_certificate" )
parser.add_argument( "--kafkaCACertificate"     , help = "the path to the kafka ca certificate"     , default = "kafka_ca_certificate" )

args = parser.parse_args()


class Producer( object ):

    def __init__( self , kafka_endpoint , access_key , access_certificate , ca_certificate ):

        self.kafka_endpoint       = kafka_endpoint

        self.kafka_producer = KafkaProducer(
                                                bootstrap_servers           = self.kafka_endpoint
                                              , value_serializer            = lambda v: json.dumps(v).encode('utf-8')
                                              , ssl_keyfile                 = access_key
                                              , ssl_certfile                = access_certificate
                                              , ssl_cafile                  = ca_certificate
                                              , security_protocol           = "SSL"
                                              , api_version_auto_timeout_ms = 10000
                                           )

    def send( self , topic , msg ):

        self.kafka_producer.send( topic , msg )


class StatsFetcher( object ):

    def __init__( self , sample_interval ):

        self.sample_interval = sample_interval

    def stats_dict( self ):

        stats_dict = cpu_stat.cpu_percents( self.sample_interval )

        # TODO: fetch other types of stats, and merge into stats_dict

        return stats_dict


producer = Producer( args.kafkaEndpoint , args.kafkaAccessKey , args.kafkaAccessCertificate , args.kafkaCACertificate )
stats_fetcher  = StatsFetcher( args.sampleInterval )

while True:

    stats = stats_fetcher.stats_dict()

    producer.send( 'os_stats' , stats )

