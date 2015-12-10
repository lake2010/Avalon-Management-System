#!/usr/bin/env python3

import json
import datetime
import sys
import importlib
sys.path.append('__AMS_LIB_PATH__')

from flask import Flask, g

from ams.sql import DataBase
from ams.miner import COLUMN_SUMMARY, COLUMN_POOLS


app = Flask(__name__)
cfgfile = '__AMS_CFG_PATH__'


def readCfg(filename):
    import configparser
    config = configparser.ConfigParser()
    config.read(filename)
    return config


cfg = readCfg(cfgfile)
db = cfg['DataBase']
farm_type = cfg['Farm']['type']
miner_type = importlib.import_module('ams.{}'.format(farm_type))
COLUMNS = {
    'summary': COLUMN_SUMMARY,
    'pool': COLUMN_POOLS,
    'device': miner_type.COLUMN_EDEVS,
    'module': miner_type.COLUMN_ESTATS,
}


def json_serial(obj):
    if isinstance(obj, datetime.datetime):
        return int(obj.timestamp())


@app.before_request
def before_request():
    g.database = DataBase(db)
    g.database.connect()


@app.route('/nodes', methods=['GET'])
def get_nodes():
    result = g.database.run('select', 'controller_config', ['ip', 'port'])
    nodes = []
    for r in result:
        nodes.append({'ip': r[0], 'port': r[1]})
    return json.dumps({'result': nodes})


@app.route('/lasttime', methods=['GET'])
def get_last_time():
    result = g.database.run('raw', 'SELECT MAX(time) FROM miner')
    return json.dumps({'result': result[0][0]}, default=json_serial)


@app.route('/config/<ip>/<port>', methods=['GET'])
def get_config(ip, port):
    import ams.luci
    clause = "`ip` = '{}'".format(ip)
    nodes = g.database.run('select', 'controller_config', ['password'], clause)
    if not nodes:
        return '{"result": "wrong node"}'
    password = nodes[0][0] if nodes[0][0] is not None else ''
    luci = ams.luci.LuCI(ip, 80, password)
    luci.auth()
    result = luci.put('uci', 'get_all', ['cgminer.default'])
    return json.dumps(result)


@app.route('/hashrate', methods=['GET'])
def get_hashrate():
    hashrate = [{'values': [], 'key': 'local'}]
    result = g.database.run('raw', 'DESCRIBE hashrate')
    for r in result[1:]:
        hashrate.append({'values': [], 'key': r[0]})
    result = g.database.run(
        'raw',
        '''\
SELECT pool.*, local.mhs
  FROM hashrate AS pool
  LEFT JOIN (
        SELECT time, sum(mhs) AS mhs
          FROM miner GROUP BY time
       )
    AS local
    ON local.time = pool.time'''
    )
    for r in result:
        hashrate[0]['values'].append({
            'x': r[0],
            'y': r[-1] * 1000000 if r[-1] is not None else 0,
        })
        for i in range(1, len(r) - 1):
            hashrate[i]['values'].append({
                'x': r[0],
                'y': r[i] * 1000000 if r[i] is not None else 0,
            })

    return json.dumps({'result': hashrate}, default=json_serial)


@app.route('/status/<table>/<time>/<ip>/<port>', methods=['GET'])
def get_status(table, time, ip, port):
    # TODO: prevent injection by checking args validation

    if time == 'latest':
        node = miner_type.Miner(ip, port, 0, log=False)
        result = node.get(table)
        status = []
        for r in result['value']:
            s = {}
            i = 0
            for column in result['column']:
                s[column] = r[i]
                i += 1
            status.append(s)
    else:
        result = g.database.run(
            'select',
            # TODO: some naming problem...
            # summary node(s) miner
            table if table != 'summary' else 'miner',
            None,
            "time = '{:%Y-%m-%d %H:%M:%S}' "
            "AND ip = '{}' AND port = '{}'".format(
                datetime.datetime.fromtimestamp(int(time)),
                ip, port
            )
        )
        status = []
        for r in result:
            s = {}
            i = 0
            for column in COLUMNS[table]:
                s[column['name']] = r[i]
                i += 1
            status.append(s)

    def sort_order(x):
        order = []
        if 'device_id' in x:
            order.append(x['device_id'])
        if 'module_id' in x:
            order.append(x['module_id'])
        if 'pool_id' in x:
            order.append(x['pool_id'])
        return order

    return json.dumps(
        {'result': sorted(status, key=sort_order)},
        default=json_serial
    )


@app.teardown_request
def teardown_request(exception):
    database = getattr(g, 'database', None)
    if database is not None:
        database.disconnect()


if __name__ == '__main__':
    app.run()