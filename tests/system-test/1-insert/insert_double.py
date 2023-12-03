import taos
import sys
import datetime
import inspect

from util.log import *
from util.sql import *
from util.cases import *
import random


class TDTestCase:

    def init(self, conn, logSql, replicaVar=1):
        self.replicaVar = int(replicaVar)
        self.db = "db1"
        tdLog.debug(f"start to excute {__file__}")
        tdSql.init(conn.cursor(), False)

    def prepare_db(self):
        tdSql.execute(f"drop database if exists {self.db}")
        tdSql.execute(f"create database {self.db}")
        tdSql.execute(f"use {self.db}")

    def case(self, table_name):
        tdSql.execute(f"drop table if exists {table_name}")
        tdSql.execute(f"create table {table_name}(ts timestamp, i1 tinyint, i2 tinyint unsigned);")

        tdSql.execute(f"insert into {table_name} values(now, -16, +6)")
        tdSql.execute(f"insert into {table_name} values(now,  80.99  ,  +0042  )")
        tdSql.execute(f"insert into {table_name} values(now,  -0042  , 80.99  )")
        tdSql.execute(f"insert into {table_name} values(now, 52.34354, 18.6)")
        tdSql.execute(f"insert into {table_name} values(now, -12.34354, +3.6)")
        tdSql.execute(f"insert into {table_name} values(now, -2.3e1, +2.324e2)")
        tdSql.execute(f"insert into {table_name} values(now, 0x40, 0b10000)")

        # str support
        tdSql.execute(f"insert into {table_name} values(now, '-16', '+6')")
        tdSql.execute(f"insert into {table_name} values(now, ' 80.99 ', '  +0042  ')")
        tdSql.execute(f"insert into {table_name} values(now, '52.34354', '18.6')")
        tdSql.execute(f"insert into {table_name} values(now, '-0x40', '+0b10010')")
        tdSql.execute(f"insert into {table_name} values(now, '-0b10010', '+0b10010')")
        tdSql.execute(f"insert into {table_name} values(now, '-12.', '+5.')")
        tdSql.execute(f"insert into {table_name} values(now, '-2.e1', '+2.e2')")
        tdSql.execute(f"insert into {table_name} values(now, '80l', '182u')")
        tdSql.execute(f"insert into {table_name} values(now, '80.99f', '0042')")

        tdSql.query(f"select * from {table_name}")
        tdSql.checkRows(16)

    def test_limit(self, table_name, dtype, bits):
        tdSql.execute(f"drop table if exists {table_name}")
        tdSql.execute(f"create table {table_name}(ts timestamp, i1 {dtype}, i2 {dtype} unsigned);")

        baseval = 2**(bits/2)
        negval = -baseval + 1.645
        posval = baseval + 4.323

        bigval = 2**(bits-1)
        max_i = bigval - 1
        min_i = -bigval
        max_u = 2*bigval - 1
        min_u = 0
        print("val:", baseval, negval, posval, max_i)
        tdSql.execute(f"insert into {table_name} values(now, {negval}, {posval})")
        tdSql.execute(f"insert into {table_name} values(now, -{baseval} , {baseval})")
        tdSql.execute(f"insert into {table_name} values(now, {max_i}, {max_u})")
        tdSql.execute(f"insert into {table_name} values(now, {min_i}, {min_u})")
        
        #fail
        # tdSql.query(f"insert into {table_name} values(now, 0, {max_u+1})")
        # tdSql.query(f"insert into {table_name} values(now, {max_i+1}, 0)")

        tdSql.query(f"select * from {table_name}")
        tdSql.checkRows(4)

    def test_tags(self, stable_name, dtype, bits):
        tdSql.execute(f"create stable {stable_name}(ts timestamp, i1 {dtype}, i2 {dtype} unsigned) tags(id {dtype})")

        baseval = 2**(bits/2)
        negval = -baseval + 1.645
        posval = baseval + 4.323

        bigval = 2**(bits-1)
        max_i = bigval - 1
        min_i = -bigval
        max_u = 2*bigval - 1
        min_u = 0
        print("val:", baseval, negval, posval, max_i)
        tdSql.execute(f"insert into {stable_name}_1 using {stable_name} tags({negval}) values(now, {negval}, {posval})")
        tdSql.execute(f"insert into {stable_name}_2 using {stable_name} tags({posval}) values(now, -{baseval} , {baseval})")
        tdSql.execute(f"insert into {stable_name}_3 using {stable_name} tags(0x40) values(now, {max_i}, {max_u})")
        tdSql.execute(f"insert into {stable_name}_4 using {stable_name} tags(0b10000) values(now, {min_i}, {min_u})")

        tdSql.query(f"select * from {stable_name}")
        tdSql.checkRows(4)

    def run(self):  # sourcery skip: extract-duplicate-method, remove-redundant-fstring
        tdSql.prepare(replica = self.replicaVar)
        self.prepare_db()
        self.case("t1")
        tdLog.printNoPrefix("==========end case1 run ...............")

        self.test_limit("t2", "bigint", 64)
        self.test_limit("t2", "int", 32)
        self.test_limit("t2", "smallint", 16)
        self.test_limit("t2", "tinyint", 8)
        tdLog.printNoPrefix("==========end case2 run ...............")

        self.test_tags("t_big", "bigint", 64)
        self.test_tags("t2_int", "int", 32)
        self.test_tags("t_small", "smallint", 16)
        self.test_tags("t_tiny", "tinyint", 8)
        tdLog.printNoPrefix("==========end case2 run ...............")

    def stop(self):
        tdSql.close()
        tdLog.success(f"{__file__} successfully executed")


tdCases.addLinux(__file__, TDTestCase())
tdCases.addWindows(__file__, TDTestCase())
