import os
import sys
import sqlite3

PATH = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(os.path.abspath(PATH + '../'))

DBFILE = PATH + 'database.sqlite'

TABLES = {
    'queue': """CREATE TABLE queue (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    DATETIME DATE DEFAULT (datetime('now','localtime')),
    MSGDATA TEXT NOT NULL)""",
}


def _init_logger(name):
    import logging
    return logging.getLogger(name)


class SQLMaster:
    def __init__(self, logger=None, debug=False):
        self.logger = logger or _init_logger('SQL-logger')
        self.conn = sqlite3.connect(DBFILE)
        self.cur = self.conn.cursor()
        self.debug = debug
        self._check_tables()

    def _check_tables(self):
        sql_tables = self.execute('select name from sqlite_master where type="table"')
        sql_tables = [table[0] for table in sql_tables]
        for table, create_cmd in TABLES.items():
            if table not in sql_tables:
                self.logger.debug('SQL: Creating table: "%s"' % table)
                try:
                    self.execute(create_cmd)
                except sqlite3.OperationalError:
                    self.logger.error('Table "%s" creation failed.' % table)

    def execute(self, cmd, *args):
        try:
            self.cur.execute(cmd, args)
        except sqlite3.OperationalError as e:
            return e
        try:
            self.conn.commit()
        except Exception as e:
            self.logger.fatal(e)
        return self.cur.fetchall()

    def load_queue(self):
        rez = self.execute('SELECT MSGDATA FROM queue')
        return [eval(row[0]) for row in rez]

    def insert_queue(self, data):
        self.execute('INSERT INTO queue(MSGDATA) VALUES (?)', data)
        return self.cur.lastrowid

    def delete_queue(self, data):
        self.execute('DELETE FROM queue WHERE MSGDATA=(?)', data)


def sql_load():
    return SQLMaster().load_queue()


def sql_insert(data):
    return SQLMaster().insert_queue(str(data))


def sql_delete(data):
    SQLMaster().delete_queue(str(data))


if __name__ == "__main__":
    sql = SQLMaster(debug=True)
    print(sql.execute('select * from queue'))
    # data = {'lol': 1, 'kek': 2, 'mem': 3}
    # sql.insert_queue(str(data))
    # sql.insert_queue(str(data))
    # m = sql.insert_queue(str(data))
    # sql.delete_queue(m)
    # # print(sql.execute('select * from queue'))
    # data_list = sql.load_queue()
    # print(data_list)
