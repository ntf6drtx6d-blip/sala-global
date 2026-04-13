
import plotly.graph_objects as go

def render_energy_battery_graph(months, reserve, generated, consumed):

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months,
        y=reserve,
        name="Battery reserve (%)",
        line=dict(color="blue", width=3),
        yaxis="y1"
    ))

    fig.add_trace(go.Scatter(
        x=months,
        y=generated,
        name="Generated (%/day)",
        line=dict(color="green"),
        yaxis="y2"
    ))

    fig.add_trace(go.Scatter(
        x=months,
        y=consumed,
        name="Consumed (%/day)",
        line=dict(color="red"),
        yaxis="y2"
    ))

    fig.update_layout(
        xaxis=dict(title="Month"),
        yaxis=dict(title="Battery (%)"),
        yaxis2=dict(title="% of battery per day", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h")
    )

    return fig
