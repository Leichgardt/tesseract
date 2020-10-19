import os
import sys
import sqlite3

PATH = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(os.path.abspath(PATH + '../'))

DBFILE = PATH + 'database.sqlite'

TABLES = {
    'queue': """CREATE TABLE queue (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    DATA TEXT NOT NULL)""",
}


class SQLMaster:
    def __init__(self, debug=False):
        self.conn = sqlite3.connect(DBFILE)
        self.cur = self.conn.cursor()
        self.debug = debug
        self._check_tables()

    def _check_tables(self):
        sql_tables = self.execute('select name from sqlite_master where type="table"')
        sql_tables = [table[0] for table in sql_tables]
        for table, create_cmd in TABLES.items():
            if table not in sql_tables:
                if self.debug:
                    print('SQL: Creating table: "%s"' % table)
                try:
                    self.execute(create_cmd)
                except sqlite3.OperationalError:
                    print('Table "%s" creation failed.' % table)

    def execute(self, cmd, *args):
        try:
            self.cur.execute(cmd, args)
        except sqlite3.OperationalError as e:
            return e
        else:
            if 'insert' in cmd[:10].lower():
                self.conn.commit()
            return self.cur.fetchall()

    def load_queue(self):
        rez = self.execute('SELECT data FROM queue')
        return [eval(row[0]) for row in rez]

    def insert_queue(self, data):
        data = str(data)
        self.execute('INSERT INTO queue(data) VALUES (?)', data)
        return self.execute('SELECT ID FROM queue WHERE data=(?) ORDER BY ID DESC LIMIT 1', data)[0][0]

    def delete_queue(self, data):
        data = str(data)
        count = self.execute('select id from queue where data=(?)', data)
        for i in range(len(count)):
            self.execute('DELETE FROM queue WHERE data=(?)', data)


def sql_load():
    sql = SQLMaster()
    return sql.load_queue()


def sql_insert(data):
    sql = SQLMaster()
    return sql.insert_queue(data)


def sql_delete(data):
    sql = SQLMaster()
    sql.delete_queue(data)


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
