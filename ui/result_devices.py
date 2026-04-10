
import plotly.graph_objects as go

def render_battery_behavior(device):
    weeks = list(range(1, len(device.get("weekly_soc", [])) + 1))
    soc = device.get("weekly_soc", [])
    recharge = device.get("weekly_recharge", [])
    discharge = device.get("weekly_discharge", [])

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=weeks, y=soc, mode="lines", name="Usable battery reserve (%)"))
    fig.add_trace(go.Scatter(x=weeks, y=recharge, mode="lines", name="Recharge (%/week)"))
    fig.add_trace(go.Scatter(x=weeks, y=discharge, mode="lines", name="Discharge (%/week)"))

    deficit_x = [w for w, r, d in zip(weeks, recharge, discharge) if r < d]
    deficit_y = [s for w, s, r, d in zip(weeks, soc, recharge, discharge) if r < d]

    if deficit_x:
        fig.add_trace(go.Scatter(x=deficit_x, y=deficit_y, mode="markers", name="Deficit regime"))

    fig.update_layout(
        title="Battery charge vs discharge behavior (weekly)",
        xaxis_title="Week",
        yaxis_title="%",
    )

    return fig
