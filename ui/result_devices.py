
import plotly.graph_objects as go

def render_graph(months, reserve, generated, consumed):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months,
        y=reserve,
        name="Battery reserve (%)",
        yaxis="y1"
    ))

    fig.add_trace(go.Scatter(
        x=months,
        y=generated,
        name="Generated (%/day)",
        yaxis="y2"
    ))

    fig.add_trace(go.Scatter(
        x=months,
        y=consumed,
        name="Consumed (%/day)",
        yaxis="y2"
    ))

    fig.update_layout(
        yaxis=dict(title="Battery (%)"),
        yaxis2=dict(title="% per day", overlaying="y", side="right"),
        xaxis=dict(title="Month")
    )

    return fig
