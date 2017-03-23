import pytest


@pytest.fixture
def app(request):
    from bigchaindb.web import server
    app = server.create_app(debug=True)
    return app


@pytest.fixture
def plugin():
    import os
    plugin_path = 'bigchaindb/common/asset/consensus.py:AssetCompositionConsensusRules'
    return '{}/{}'.format(os.getcwd().split('/tests')[0], plugin_path)


@pytest.fixture
def plugin_policy():
    import os
    plugin_path = 'bigchaindb/common/asset/consensus.py:AssetPolicyConsensusRules'
    return '{}/{}'.format(os.getcwd().split('/tests')[0], plugin_path)


@pytest.fixture
def b_consensus(plugin):
    from bigchaindb import Bigchain
    return Bigchain(consensusPlugin=plugin)


@pytest.fixture
def b_policy(plugin_policy):
    from bigchaindb import Bigchain
    return Bigchain(consensusPlugin=plugin_policy)

