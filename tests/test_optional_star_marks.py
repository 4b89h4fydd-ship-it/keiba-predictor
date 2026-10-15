"""The optional fifth mark comes from the same observed ranking, not legacy scores."""
import unittest
from unittest.mock import patch
from arvexq.prediction.observed_model import apply_observed_marks, NAR_MODEL_VERSION


class TestOptionalStar(unittest.TestCase):
    def test_observed_star_requires_margin_and_position_support(self):
        horses=[{"horseNumber":i,"integratedEvaluation":{}} for i in range(1,7)]
        detail={"circuit":"地方","horses":horses}
        scores=[.90,.84,.78,.70,.67,.51]
        rows=[{"horse":h,"score":scores[i],"rank":i+1,"sample":5,
               "factors":{"mineta":.60,"margin":scores[i]},
               "marginCoverage":.8,"modelVersion":NAR_MODEL_VERSION}
              for i,h in enumerate(horses)]
        with patch("arvexq.prediction.observed_model.rank_observed",return_value=rows):
            apply_observed_marks(detail)
        self.assertEqual([h["integratedEvaluation"]["mark"] for h in horses],
                         ["◎","○","▲","△","☆",""])


if __name__=="__main__":unittest.main()
