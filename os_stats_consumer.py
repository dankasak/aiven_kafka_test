import argparse , json , psycopg2 , time , logging

from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient , NewTopic

# logging.basicConfig( level=logging.DEBUG )

parser = argparse.ArgumentParser()

parser.add_argument( "--pgHost"                 , help = "Host of Postgres instance"                , default = "pg-39d6f834-project-ffc3.aivencloud.com" )
parser.add_argument( "--pgPort"                 , help = "Port of Postgres instance"                , default = "24742" )
parser.add_argument( "--pgDatabase"             , help = "Postgres database"                        , default = "defaultdb" )
parser.add_argument( "--pgUsername"             , help = "Postgres username"                        , default = "avnadmin" )
parser.add_argument( "--pgPassword"             , help = "Postgres password"                        , default = "ypuqxq1omnp6focm" )

parser.add_argument( "--kafkaEndpoint"          , help = "the endpoint of the kafka service"        , default = "kafka-bd35e9a-project-ffc3.aivencloud.com:24744" )
parser.add_argument( "--kafkaAccessKey"         , help = "the path to the kafka access key"         , default = "kafka_access_key" )
parser.add_argument( "--kafkaAccessCertificate" , help = "the path to the kafka access certificate" , default = "kafka_access_certificate" )
parser.add_argument( "--kafkaCACertificate"     , help = "the path to the kafka ca certificate"     , default = "kafka_ca_certificate" )

args = parser.parse_args()

class Consumer( object ):

    def __init__( self , kafka_endpoint , access_key , access_certificate , ca_certificate ):

        self.kafka_endpoint = kafka_endpoint

        self.kafka_consumer = KafkaConsumer(
                                                bootstrap_servers           = self.kafka_endpoint
                                              , value_deserializer          = lambda m: json.loads( m.decode('utf-8') )
                                              , ssl_keyfile                 = access_key
                                              , ssl_certfile                = access_certificate
                                              , ssl_cafile                  = ca_certificate
                                              , security_protocol           = "SSL"
                                              , api_version_auto_timeout_ms = 10000
                                           )

        topics = self.kafka_consumer.topics()

        if 'os_stats' not in topics:

            print( "os_stats topic not found ... creating" )

            admin_client = KafkaAdminClient(
                                                bootstrap_servers           = self.kafka_endpoint
                                              , ssl_keyfile                 = access_key
                                              , ssl_certfile                = access_certificate
                                              , ssl_cafile                  = ca_certificate
                                              , security_protocol           = "SSL"
                                              , api_version_auto_timeout_ms = 10000
                                           )

            topic_list = []
            topic_list.append(NewTopic( name = "os_stats" , num_partitions = 1 , replication_factor = 1 ) )
            admin_client.create_topics( new_topics = topic_list , validate_only = False )

        self.kafka_consumer.subscribe( 'os_stats' )

    def fetch_messages( self ):

        for msg in self.kafka_consumer:
            yield msg


class PostgresWriter( object ):

    def __init__( self , connect_info ):

        self.connect_info = connect_info
        self.connection   = self.connect( connect_info )
        self.check_create_schema()

    def connect( self , connect_info ):

        tries = 5

        for t in range(tries):

            try:

                print( "Attempting connection to {0}".format( connect_info['host'] ) )
                connection    = psycopg2.connect(
                    user      = connect_info['username']
                  , password  = connect_info['password']
                  , host      = connect_info['host']
                  , port      = connect_info['port']
                  , database  = connect_info['database']
                )
                # spec requires the default to be that all cursors will begin a transaction - we don't want this
                connection.set_session( autocommit = True )
                return connection

            except psycopg2.OperationalError as e:

                if t+1 == tries:
                    raise e
                else:
                    print( "Attempt [{0}] failed: {1}. Sleeping and retrying".format( t, e ) )
                    time.sleep( 3 )

    def fetch_table_list( self ):

        cursor = self.connection.cursor()

        self.execute(
            cursor
          , "select table_name from information_schema.tables where table_type like '%TABLE'" # don't care about schemas for now
          , {}
        )

        tables_list = []

        for record in cursor:
            tables_list.append( record[0] )

        return tables_list

    def check_create_schema( self ):

        cursor = self.connection.cursor()

        tables = self.fetch_table_list()

        if "stats" in tables:
            return

        print( "Postgtes stats table not found ... creating" )

        self.execute(
            cursor
          , """create table stats (
                   id           serial
                 , stat_ts      timestamp default now()
                 , stat_type    varchar(100)
                 , stat_value   double precision
               )"""
        )

        self.execute(
            cursor
          , "create index IDX_STAT_LOOKUP on stats ( stat_ts , stat_type )"
        )

    def execute( self , cursor , sql , params = {} ):

        # print( sql )

        if len( params ) == 0:
            cursor.execute( sql )
        else:
            # print( json.dumps( params ) )
            cursor.execute( sql , params )

    def send( self , consumer_record ):

        cursor = self.connection.cursor()

        stats_dict = consumer_record.value

        # TODO: assemble stats into batches of 100 and stream via pg_put_copy_data?
        for stat_type in stats_dict:
            self.execute(
                cursor
              , "insert into stats ( stat_type , stat_value ) values ( %(stat_type)s , %(stat_value)s )"
              , { 'stat_type': stat_type , 'stat_value': stats_dict[ stat_type  ] }
            )


consumer  = Consumer( args.kafkaEndpoint , args.kafkaAccessKey , args.kafkaAccessCertificate , args.kafkaCACertificate )

pg_connect_info = {
    'username':    args.pgUsername
  , 'password':    args.pgPassword
  , 'host':        args.pgHost
  , 'port':        args.pgPort
  , 'database':    args.pgDatabase
}

pg_writer     = PostgresWriter( pg_connect_info )

for consumer_record in consumer.fetch_messages():
    pg_writer.send( consumer_record )
