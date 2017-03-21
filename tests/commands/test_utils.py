import argparse
from argparse import ArgumentTypeError, Namespace
import logging
from logging import getLogger

import pytest

from unittest.mock import patch


@pytest.fixture
def reset_bigchaindb_config(monkeypatch):
    import bigchaindb
    monkeypatch.setattr('bigchaindb.config', bigchaindb._config)


@pytest.mark.usefixtures('ignore_local_config_file', 'reset_bigchaindb_config')
def test_configure_bigchaindb_configures_bigchaindb(mocked_setup_logging):
    from bigchaindb.commands.utils import configure_bigchaindb
    from bigchaindb.config_utils import is_configured
    assert not is_configured()

    @configure_bigchaindb
    def test_configure(args):
        assert is_configured()

    args = Namespace(config=None)
    test_configure(args)
    mocked_setup_logging.assert_called_once_with(user_log_config={})


@pytest.mark.usefixtures('ignore_local_config_file',
                         'reset_bigchaindb_config',
                         'reset_logging_config')
@pytest.mark.parametrize('log_level', (
    logging.DEBUG,
    logging.INFO,
    logging.WARNING,
    logging.ERROR,
    logging.CRITICAL,
))
def test_configure_bigchaindb_configures_logging(log_level,
                                                 mocked_setup_sub_logger):
    from bigchaindb.commands.utils import configure_bigchaindb
    from bigchaindb.log.configs import PUBLISHER_LOGGING_CONFIG
    root_logger = getLogger()
    assert root_logger.level == logging.NOTSET

    @configure_bigchaindb
    def test_configure_logger(args):
        root_logger = getLogger()
        assert root_logger.level == PUBLISHER_LOGGING_CONFIG['root']['level']

    args = Namespace(config=None, log_level=log_level)
    test_configure_logger(args)
    mocked_setup_sub_logger.assert_called_once_with(
        user_log_config={'level_console': log_level})


def test_start_raises_if_command_not_implemented():
    from bigchaindb.commands import utils
    from bigchaindb.commands.bigchain import create_parser

    parser = create_parser()

    with pytest.raises(NotImplementedError):
        # Will raise because `scope`, the third parameter,
        # doesn't contain the function `run_start`
        utils.start(parser, ['start'], {})


def test_start_raises_if_no_arguments_given():
    from bigchaindb.commands import utils
    from bigchaindb.commands.bigchain import create_parser

    parser = create_parser()

    with pytest.raises(SystemExit):
        utils.start(parser, [], {})


@patch('multiprocessing.cpu_count', return_value=42)
def test_start_sets_multiprocess_var_based_on_cli_args(mock_cpu_count):
    from bigchaindb.commands import utils

    def run_mp_arg_test(args):
        return args

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(title='Commands',
                                      dest='command')
    mp_arg_test_parser = subparser.add_parser('mp_arg_test')
    mp_arg_test_parser.add_argument('-m', '--multiprocess',
                                    nargs='?',
                                    type=int,
                                    default=False)

    scope = {'run_mp_arg_test': run_mp_arg_test}
    assert utils.start(parser, ['mp_arg_test'], scope).multiprocess == 1
    assert utils.start(parser, ['mp_arg_test', '--multiprocess'], scope).multiprocess == 42


def test_mongodb_host_type():
    from bigchaindb.commands.utils import mongodb_host

    # bad port provided
    with pytest.raises(ArgumentTypeError):
        mongodb_host('localhost:11111111111')

    # no port information provided
    with pytest.raises(ArgumentTypeError):
        mongodb_host('localhost')

    # bad host provided
    with pytest.raises(ArgumentTypeError):
        mongodb_host(':27017')
