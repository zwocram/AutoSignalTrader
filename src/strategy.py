

class Strategy:
    def __init__(self, risklevel, portfolioheat, select_tp_level, select_tp_level_explanation, split_position_size):
        self.risklevel = risklevel
        self.portfolioheat = portfolioheat
        self.tpLevel = select_tp_level
        self.tpLevelExplanation = select_tp_level_explanation
        self.splitPositionSize = split_position_size

