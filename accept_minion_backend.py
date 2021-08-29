import salt.config
import salt.key
import salt.wheel

from flask import Flask, jsonify
app = Flask(__name__)

master_opts = salt.config.client_config('/etc/salt/master')
skey = salt.key.Key(master_opts)

@app.route('/api/check_pre/<string:minion_id>/')
def check_pre(minion_id):
    pre_keys = skey.list_keys()['minions_pre']
    if minion_id in pre_keys:
        return jsonify(pre=True)
    return jsonify(pre=False)

@app.route('/api/accept_key/<string:minion_id>/')
def accept_key(minion_id):
    if check_pre(minion_id):
        wheel = salt.wheel.WheelClient(master_opts)
        wheel.cmd('key.accept', [minion_id])
        return jsonify(accept=True)
    return jsonify(accept=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(80))