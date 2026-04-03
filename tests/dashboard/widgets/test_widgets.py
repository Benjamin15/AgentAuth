import pandas as pd

from agentauth.dashboard.widgets.charts import ErrorDistWidget, LatencyHeatWidget, SpendDistWidget
from agentauth.dashboard.widgets.metrics import (
    ActiveAgentsWidget,
    AverageLatencyWidget,
    MonthlySpendWidget,
    TotalRequestsWidget,
)
from agentauth.dashboard.widgets.tables import AgentStatusTableWidget


def test_metrics_rendering_v3():
    df = pd.DataFrame({"latency": [10, 20], "cost": [0.1, 0.2]})
    data = {"df": df, "agents": []}

    # Total Requests
    m1 = TotalRequestsWidget().render(data)
    assert "2" in str(m1)

    # Avg Latency
    m2 = AverageLatencyWidget().render(data)
    assert "15ms" in str(m2)

    # Active Agents
    m3 = ActiveAgentsWidget().render(data)
    assert "0/0" in str(m3)

    # Monthly Spend
    m4 = MonthlySpendWidget().render(data)
    assert "$0.30" in str(m4)


def test_charts_rendering_v3():
    # Spend Distribution
    g = SpendDistWidget().render({"df": pd.DataFrame(), "agents": []})
    assert g is not None

    # Error Distribution
    e = ErrorDistWidget().render({"df": pd.DataFrame()})
    assert e is not None

    # Latency Heatmap
    h = LatencyHeatWidget().render({"df": pd.DataFrame(), "agents": []})
    assert h is not None


def test_tables_rendering_v3():
    # Empty
    t = AgentStatusTableWidget().render({"agents": [], "logs": []})
    assert "Status" in str(t)

    # With data
    class MockAgent:
        id = 1
        name = "Bot"
        is_frozen = False
        permissions = []
        monthly_budget_usd = 100.0

    t_data = AgentStatusTableWidget().render({"agents": [MockAgent()], "logs": []})
    assert "Bot" in str(t_data)


def test_widget_error_states():
    # Test widgets with None/empty data
    assert "Spend Distribution" in str(
        SpendDistWidget().render({"df": pd.DataFrame(), "agents": []})
    )
    assert "Error Code" in str(ErrorDistWidget().render({"df": pd.DataFrame()}))
