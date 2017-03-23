from bigchaindb.common.exceptions import ValidationError
from bigchaindb.consensus import BaseConsensusRules
from bigchaindb.models import Transaction

ASSET_TYPE_MIX = 'mix'
ASSET_TYPE_PURE = 'pure'
ASSET_TYPE_COMPOSITION = 'composition'

ASSET_TYPES = [
    ASSET_TYPE_MIX,
    ASSET_TYPE_PURE,
    ASSET_TYPE_COMPOSITION
]


class AssetCompositionConsensusRules(BaseConsensusRules):

    @staticmethod
    def validate_transaction(bigchain, transaction):

        input_txs = None
        if transaction.operation == Transaction.TRANSFER:
            input_txs = transaction.get_input_txs(bigchain)

        AssetCompositionConsensusRules\
            .validate_asset(bigchain, transaction, input_txs)

        return transaction.validate(bigchain, input_txs)

    @staticmethod
    def validate_asset(bigchain, transaction, input_txs):
        assets = AssetCompositionConsensusRules\
            .resolve_asset(bigchain, transaction, input_txs)

        asset_types = set(
            [asset['data']['type']
             for asset in assets
             if 'data' in asset and asset['data'] is not None
             and 'type' in asset['data'] and asset['data']['type'] is not None
             and asset['data']['type'] in ASSET_TYPES])

        asset_type = ASSET_TYPE_PURE
        if len(asset_types) == 1:
            asset_type = asset_types.pop()
        if len(asset_types) > 1:
            raise ValidationError('Cannot mix assets')

        if asset_type == ASSET_TYPE_PURE:
            return AssetCompositionConsensusRules\
                .validate_pure(bigchain, transaction, input_txs)
        elif asset_type == ASSET_TYPE_MIX:
            return AssetCompositionConsensusRules\
                .validate_mix(bigchain, transaction, input_txs)
        elif asset_type == ASSET_TYPE_COMPOSITION:
            return AssetCompositionConsensusRules\
                .validate_composition(bigchain, transaction, input_txs)

    @staticmethod
    def validate_pure(bigchain, transaction, input_txs):
        if transaction.operation == Transaction.TRANSFER:
            transaction.validate_asset(
                bigchain,
                [input_tx
                 for (input_, input_tx, status)
                 in input_txs if input_tx is not None])

            AssetCompositionConsensusRules\
                .validate_amount_conservation(transaction, input_txs)

        return transaction

    @staticmethod
    def validate_mix(bigchain, transaction, input_txs):
        if transaction.operation == Transaction.TRANSFER:
            pass
        return transaction

    @staticmethod
    def validate_composition(bigchain, transaction, input_txs):
        if transaction.operation == Transaction.TRANSFER:
            AssetCompositionConsensusRules \
                .validate_amount_conservation(transaction, input_txs)

        return transaction

    @staticmethod
    def validate_amount_conservation(transaction, input_txs):
        transaction.validate_amount(
            [input_tx.outputs[input_.fulfills.output]
             for (input_, input_tx, status)
             in input_txs if input_tx is not None])

    @staticmethod
    def resolve_asset(bigchain, transaction, input_txs):
        if not hasattr(transaction, 'asset'):
            raise ValidationError('Asset not found in transaction {}'.format(transaction))

        if transaction.operation == Transaction.CREATE:
            return [transaction.asset]
        elif transaction.operation == Transaction.TRANSFER:
            asset_ids = transaction.get_asset_ids(
                [input_tx
                 for (input_, input_tx, status)
                 in input_txs if input_tx is not None])
            return [bigchain.get_transaction(asset_id).asset for asset_id in asset_ids]


class AssetPolicyConsensusRules(AssetCompositionConsensusRules):
    @staticmethod
    def validate_transaction(bigchain, transaction):
        result = AssetCompositionConsensusRules\
            .validate_transaction(bigchain, transaction)
        AssetPolicyConsensusRules\
            .validate_policy(transaction, bigchain)
        return result

    @staticmethod
    def is_clean_script(script):
        if 'bigchain.' in script:
            if 'bigchain.get_' not in script:
                return False
        if 'while' in script:
            return False
        # if 'for' in script:
        #     return False
        if 'wait' in script:
            return False
        return True

    @staticmethod
    def validate_policy(transaction, bigchain):
        if not hasattr(transaction, 'asset'):
            raise ValidationError('Asset not found in transaction {}'.format(transaction))

        asset = transaction.asset
        if not asset:
            return transaction

        if 'id' in asset:
            create_tx = bigchain.get_transaction(asset['id'])
            asset = create_tx.asset

        asset_data = asset['data']

        if asset_data and 'script' in asset_data:
            script = asset_data['script']

            if not AssetPolicyConsensusRules.is_clean_script(script):
                raise ValidationError('Asset script might contain malicious code:\n{}'.format(script))

            try:
                # do not allow builtins or other funky business
                context = {
                    'print': print,
                    'len': len
                }

                # WARNING!!!! DANGER!!!! NOT FOR PRODUCTION
                exec(script, {"__builtins__": context}, {'bigchain': bigchain, 'self': transaction})
                return transaction

            except Exception as e:
                raise ValidationError('Asset script evaluation failed with {} : {}'
                                      .format(e.__class__.__name__, e).rstrip())
        else:
            # No script, asset is always valid
            return transaction
