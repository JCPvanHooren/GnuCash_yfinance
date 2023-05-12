import helpers
import getpass
from sqlalchemy import URL, create_engine, MetaData, Table, select
from sqlalchemy.sql import func

class MDB:
    def __init__(self, host, port, database):
        self._host = host
        self._port = port
        self._database = database
        
        # Create MariaDB SQLAlchemy Engine
        self._create_engine()
        self._get_commodities()
    
    @property
    def host(self):
        return self._host
    
    @property
    def port(self):
        return self._port
    
    @property
    def database(self):
        return self._database
    
    @property
    def engine(self):
        return self._engine
    
    @property
    def commodities(self):
        return self._commodities
    
    def _get_username(self):
        default_user = getpass.getuser().title()
        print(f"\nEnter a username and password to connect to: MariaDB://{self.host}:{self.port}/{self.database}")
        return input(f"Provide username or hit 'Enter' to use default ({default_user}): ") or default_user
    
    def _get_password(self):
        pwd = getpass.getpass()
        while not pwd: pwd = getpass.getpass('Password cannot be empty. Please enter a Password: ')
        return pwd
    
    def _create_engine(self):
        _mdb_usr = self._get_username()
        _mdb_pwd = self._get_password()
        url_object = URL.create('mariadb+pymysql',
                                            username = _mdb_usr,
                                            password = _mdb_pwd,
                                            host = self.host,
                                            port = self.port,
                                            database = self.database)
        self._engine = create_engine(url_object)
    
    def _get_commodities(self):
        # Read MetaData from GnuCash tables through 'table reflection'
        # https://docs.sqlalchemy.org/en/20/tutorial/metadata.html#table-reflection
        metadata_obj = MetaData()
        commodities_table = Table('commodities', metadata_obj, autoload_with = self.engine)
        prices_table = Table('prices', metadata_obj, autoload_with = self.engine)
        
        # Build SELECT SQL statement through SQLAlchemy to select commodities
        sql_stmt = (select(commodities_table.c.guid,
                            commodities_table.c.namespace,
                            commodities_table.c.mnemonic,
                            commodities_table.c.fullname,
                            prices_table.c.currency_guid,
                            func.date(func.max(prices_table.c.date)).label('last_price_date'),
                            prices_table.c.value_denom)
                    .select_from(commodities_table)
                    .join(prices_table, commodities_table.c.guid == prices_table.c.commodity_guid)
                    .where(commodities_table.c.namespace != 'template')
                    .where(commodities_table.c.mnemonic != 'EUR')
                    .where(commodities_table.c.mnemonic != 'CHE')
                    .group_by(commodities_table.c.mnemonic))
        
        with self.engine.connect() as conn:
            self._commodities = conn.execute(sql_stmt)

if __name__ == '__main__':
    args = helpers.Args()
    mdb = MDB(args.host, args.port, args.database)
    print('Selecting Commodities from GnuCash @ MariaDB... ', end = '')
    print('SELECTED')
    helpers.print_headerline("=", False)
    for commodity in mdb.commodities:
        print(commodity)