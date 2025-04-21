

class Strategy:
    def __init__(self, risklevel, portfolioheat, select_tp_level, select_tp_level_explanation, split_position_size, use_fixed_risk_amount, fixed_risk_amount):
        self.risklevel = risklevel
        self.portfolioheat = portfolioheat
        self.tpLevel = select_tp_level
        self.tpLevelExplanation = select_tp_level_explanation
        self.splitPositionSize = split_position_size
        self.useFixedRiskAmount = use_fixed_risk_amount
        self.fixedRiskAmount = fixed_risk_amount

