"""If run as main module (not imported), execute:

    1. Parse cli arguments
    2. Create MariaDB SqlAlchemy Engine
    3. Get GnuCash Commodities from MariaDB
    4. Print Commodities to STDOUT

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import getpass

from sqlalchemy import URL, create_engine, MetaData, Table, select, Engine
from sqlalchemy.sql import func

import helpers

class MDB:
    """Manage GnuCash @ MariaDB connection, properties and selected data"""
    def __init__(self, _args: helpers.Args) -> None:
        """Initialize MariaDB connection, using host, port and database arguments

        Create MariaDB SqlAlchemy Engine and get commodities.

        Args:
            _args: Processed arguments from cli and/or `config.ini`

        """

        self._host = _args.host
        self._port = _args.port
        self._database = _args.database

        # Create MariaDB SQLAlchemy Engine
        self._create_engine(_args.user, _args.pwd)
        self._get_commodities()

    @property
    def host(self) -> str:
        """MariaDB host name or IP-address"""
        return self._host

    @property
    def port(self) -> int:
        """MariaDB port"""
        return self._port

    @property
    def database(self) -> str:
        """GnuCash database name"""
        return self._database

    @property
    def engine(self) -> Engine:
        """SqlAlchemy MariaDB Engine"""
        return self._engine

    @property
    def commodities(self):
        """GnuCash Commodities from MariaDB"""
        return self._commodities

    def _get_username(self) -> str:
        """Get MariaDB username from user. Defaults to current system user."""
        default_user = getpass.getuser().title()
        print(
            f"\nEnter a username and password to connect to: "
            f"MariaDB://{self.host}:{self.port}/{self.database}"
        )
        return input(
            f"Provide username or hit 'Enter' to use default "
            f"({default_user}): ") or default_user

    def _get_password(self) -> str:
        """Get MariaDB password from user."""
        pwd = getpass.getpass()
        while not pwd:
            pwd = getpass.getpass('Password cannot be empty. Please enter a Password: ')
        return pwd

    def _create_engine(self, user, pwd) -> None:
        """Create SqlAlchemy MariaDB Engine"""
        _mdb_usr = self._get_username() if user is None else user
        _mdb_pwd = self._get_password() if pwd is None else pwd
        url_object = URL.create('mariadb+pymysql',
                                            username = _mdb_usr,
                                            password = _mdb_pwd,
                                            host = self.host,
                                            port = self.port,
                                            database = self.database)
        self._engine = create_engine(url_object)

    def _get_commodities(self) -> None:
        """Get commodities from GnuCash @ MariaDB"""
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
    mdb = MDB(args)
    print('Selecting Commodities from GnuCash @ MariaDB... ', end = '')
    print('SELECTED')
    helpers.print_headerline("=", False)
    for commodity in mdb.commodities:
        print(commodity)
