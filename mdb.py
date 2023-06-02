"""If run as main module (not imported), execute:

    1. Parse cli arguments
    2. Create MariaDB SqlAlchemy Engine
    3. Get GnuCash Commodities from MariaDB
    4. Print Commodities to STDOUT

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

from sqlalchemy import URL, create_engine as sqla_create_engine, MetaData, Table, select, Engine
from sqlalchemy.sql import func

import helpers
import config

def create_engine(connection_cfg: object, database: str) -> Engine:
    """Create SqlAlchemy MariaDB Engine.

    Args:
        connection_cfg: host, port, user and pwd to connect with.
        database: database to connect to.

    """

    url_object = URL.create(
        'mariadb+pymysql',
        username = connection_cfg.user,
        password = connection_cfg.pwd,
        host = connection_cfg.host,
        port = connection_cfg.port,
        database = database
    )
    print(url_object)
    return sqla_create_engine(url_object)

def get_commodities(engine: Engine):
    """Get commodities from GnuCash @ MariaDB.

    Args:
        engine: SqlAlchemy engine to run query against.

    """

    # Read MetaData from GnuCash tables through 'table reflection'
    # https://docs.sqlalchemy.org/en/20/tutorial/metadata.html#table-reflection
    metadata_obj = MetaData()
    commodities_table = Table('commodities', metadata_obj, autoload_with = engine)
    prices_table = Table('prices', metadata_obj, autoload_with = engine)

    # Build SELECT SQL statement through SQLAlchemy to select commodities
    sql_stmt = (select(commodities_table.c.guid,
                        commodities_table.c.namespace,
                        commodities_table.c.mnemonic,
                        commodities_table.c.fullname,
                        prices_table.c.currency_guid,
                        func.date(func.max(prices_table.c.date)).label('last_price_date'), # pylint: disable-msg=E1102
                        prices_table.c.value_denom)
                .select_from(commodities_table)
                .join(prices_table, commodities_table.c.guid == prices_table.c.commodity_guid)
                .where(commodities_table.c.namespace != 'template')
                .where(commodities_table.c.mnemonic != 'EUR')
                .where(commodities_table.c.mnemonic != 'CHE')
                .group_by(commodities_table.c.mnemonic))

    with engine.connect() as conn:
        return conn.execute(sql_stmt)

if __name__ == '__main__':
    general_cfg, conn_cfg, gnucash_cfg, data_cfg, yf_cfg = config.process_config()
    gnucash_engine = create_engine(conn_cfg, gnucash_cfg.database)
    commodities = get_commodities(gnucash_engine)

    print('Selecting Commodities from GnuCash @ MariaDB... ', end = '')
    print('SELECTED')
    helpers.print_headerline("=", False)
    for commodity in commodities:
        print(commodity)
