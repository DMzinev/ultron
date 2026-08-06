from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RkmRule, RkmRuleInstance

class RuleAPI:
    @staticmethod
    def get_rules(store: RepositoryStore) -> list[RkmRule]:
        return store.get_rules()

    @staticmethod
    def get_rule_instances(store: RepositoryStore) -> list[RkmRuleInstance]:
        return store.get_rule_instances()
