"""Local Dash chat, provider authentication and sales dashboard."""

from __future__ import annotations

from typing import Any

from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from operatix.application.repositories import build_repository
from operatix.application.sales_agent import SalesAgent
from operatix.config import Settings, load_local_env
from operatix.llm.providers import (
    PROVIDER_SPECS,
    Provider,
    build_chat_model,
    friendly_provider_error,
    provider_is_configured,
    resolve_model_name,
)
from operatix.presentation.dashboard import sales_summary


def _provider_options() -> list[dict[str, str]]:
    options = []
    for provider, spec in PROVIDER_SPECS.items():
        state = "configurado" if provider_is_configured(provider) else "sin configurar"
        options.append({"label": f"{spec.label} · {state}", "value": provider.value})
    return options


def _render_chat(history: list[dict[str, str]]) -> list[Any]:
    return [
        html.Div(
            [
                html.Span("Tú" if item["role"] == "user" else "OPERATIX", className="bubble-role"),
                html.P(item["content"]),
            ],
            className=f"chat-bubble {item['role']}",
        )
        for item in history
    ]


def _metric_cards(metrics: dict[str, object]) -> list[Any]:
    cards = [
        ("Transacciones", metrics["transactions"]),
        ("Unidades", metrics["units"]),
        ("Importe", f"{metrics['currency']} {metrics['total']:,.2f}"),
    ]
    return [
        html.Div([html.Span(label), html.Strong(value)], className="metric-card")
        for label, value in cards
    ]


def create_app() -> Dash:
    load_local_env()
    settings = Settings.from_env()
    _, empty_figure = sales_summary([])

    app = Dash(__name__, title="OPERATIX")
    app.layout = html.Div(
        [
            dcc.Store(id="chat-history", data=[]),
            html.Aside(
                [
                    html.Div(
                        [html.Div("O", className="brand-mark"), html.H1("OPERATIX")],
                        className="brand",
                    ),
                    html.P("Configuración local", className="eyebrow"),
                    html.Label("Proveedor de IA"),
                    dcc.Dropdown(
                        id="provider",
                        options=_provider_options(),
                        value=Provider.OPENAI.value,
                        clearable=False,
                    ),
                    html.Label("Modelo"),
                    dcc.Input(
                        id="model-name",
                        value=resolve_model_name(Provider.OPENAI),
                        type="text",
                        debounce=True,
                    ),
                    html.Label("Método de autenticación"),
                    dcc.RadioItems(
                        id="auth-method",
                        options=[
                            {"label": " Variable de entorno", "value": "environment"},
                            {"label": " Clave temporal", "value": "temporary"},
                        ],
                        value="environment",
                    ),
                    dcc.Input(
                        id="temporary-api-key",
                        type="password",
                        placeholder="Clave solo para esta ejecución",
                        persistence=False,
                        style={"display": "none"},
                    ),
                    html.Div(id="provider-help", className="provider-help"),
                    html.Hr(),
                    html.Label("Almacenamiento"),
                    dcc.Dropdown(
                        id="storage-backend",
                        options=[
                            {"label": "Excel local", "value": "excel"},
                            {"label": "Google Sheets", "value": "google_sheets"},
                        ],
                        value=settings.storage_backend,
                        clearable=False,
                    ),
                    html.Div(
                        [
                            html.Label("Archivo Excel"),
                            dcc.Input(id="excel-path", value=str(settings.excel_path), type="text"),
                        ],
                        id="excel-settings",
                    ),
                    html.Div(
                        [
                            html.Label("ID de la hoja"),
                            dcc.Input(
                                id="spreadsheet-id",
                                value=settings.google_spreadsheet_id or "",
                                type="text",
                            ),
                            html.Label("Credenciales de servicio"),
                            dcc.Input(
                                id="credentials-path",
                                value=str(settings.google_credentials_path),
                                type="text",
                            ),
                        ],
                        id="google-settings",
                        style={"display": "none"},
                    ),
                    html.Label("Pestaña"),
                    dcc.Input(id="worksheet", value=settings.google_worksheet, type="text"),
                    html.P(
                        "Las claves temporales no se escriben en disco. "
                        "Para compartir la aplicación, usa OAuth o un gestor de secretos.",
                        className="security-note",
                    ),
                ],
                className="sidebar",
            ),
            html.Main(
                [
                    html.Header(
                        [
                            html.P("AGENTE DE AUTOMATIZACIÓN EMPRESARIAL", className="eyebrow"),
                            html.H2("Registra una venta hablando con tus datos"),
                            html.P(
                                "El agente estructura el pedido, ejecuta la herramienta "
                                "y conserva una transacción auditable.",
                                className="subtitle",
                            ),
                        ]
                    ),
                    html.Section(
                        [
                            html.Div(id="chat-window", children=[], className="chat-window"),
                            dcc.Textarea(
                                id="message-input",
                                value=(
                                    "Agrega una venta de 5 laptops por $2500 "
                                    "para el cliente Juan Perez"
                                ),
                                placeholder="Escribe un pedido…",
                            ),
                            html.Div(
                                [
                                    html.Button("Procesar pedido", id="send-button", n_clicks=0),
                                    html.Div(id="status", className="status"),
                                ],
                                className="composer-actions",
                            ),
                        ],
                        className="chat-panel",
                    ),
                    html.Section(
                        [
                            html.Div(
                                id="metrics",
                                children=_metric_cards(
                                    {
                                        "transactions": 0,
                                        "units": 0,
                                        "currency": "USD",
                                        "total": 0.0,
                                    }
                                ),
                                className="metrics",
                            ),
                            dcc.Graph(
                                id="sales-chart",
                                figure=empty_figure,
                                config={"displayModeBar": False},
                            ),
                        ],
                        className="dashboard-panel",
                    ),
                ],
                className="workspace",
            ),
        ],
        className="app-shell",
    )

    @app.callback(
        Output("provider-help", "children"),
        Output("model-name", "value"),
        Output("temporary-api-key", "style"),
        Input("provider", "value"),
        Input("auth-method", "value"),
    )
    def update_provider(provider_value: str, auth_method: str):
        provider = Provider(provider_value)
        spec = PROVIDER_SPECS[provider]
        configured = provider_is_configured(provider)
        help_content = [
            html.Strong("Listo. " if configured else "Falta autenticación. "),
            html.Span(spec.auth_hint + " "),
            html.A("Abrir consola", href=spec.credentials_url, target="_blank"),
        ]
        key_style = (
            {"display": "block", "width": "100%"}
            if auth_method == "temporary"
            else {"display": "none"}
        )
        return help_content, resolve_model_name(provider), key_style

    @app.callback(
        Output("excel-settings", "style"),
        Output("google-settings", "style"),
        Input("storage-backend", "value"),
    )
    def update_storage(backend: str):
        if backend == "google_sheets":
            return {"display": "none"}, {"display": "block"}
        return {"display": "block"}, {"display": "none"}

    @app.callback(
        Output("chat-history", "data"),
        Output("chat-window", "children"),
        Output("status", "children"),
        Output("sales-chart", "figure"),
        Output("metrics", "children"),
        Input("send-button", "n_clicks"),
        State("message-input", "value"),
        State("provider", "value"),
        State("model-name", "value"),
        State("auth-method", "value"),
        State("temporary-api-key", "value"),
        State("storage-backend", "value"),
        State("excel-path", "value"),
        State("spreadsheet-id", "value"),
        State("credentials-path", "value"),
        State("worksheet", "value"),
        State("chat-history", "data"),
        prevent_initial_call=True,
    )
    def submit_message(
        _clicks: int,
        message: str,
        provider: str,
        model_name: str,
        auth_method: str,
        temporary_key: str | None,
        backend: str,
        excel_path: str,
        spreadsheet_id: str,
        credentials_path: str,
        worksheet: str,
        history: list[dict[str, str]],
    ):
        if not message or not message.strip():
            raise PreventUpdate

        history = list(history or [])
        history.append({"role": "user", "content": message.strip()})
        supplied_key = temporary_key if auth_method == "temporary" else None
        try:
            repository = build_repository(
                settings,
                backend=backend,
                excel_path=excel_path,
                spreadsheet_id=spreadsheet_id,
                credentials_path=credentials_path,
                worksheet=worksheet,
            )
            model = build_chat_model(provider, model_name, supplied_key)
            outcome = SalesAgent(model, repository).process(message)
            history.append({"role": "assistant", "content": outcome.message})
            metrics, figure = sales_summary(repository.list_all())
            state = "Venta registrada" if outcome.inserted else "Solicitud procesada"
            return history, _render_chat(history), state, figure, _metric_cards(metrics)
        except Exception as exc:  # Dash must turn integration failures into user feedback.
            safe_error = friendly_provider_error(exc)
            if supplied_key:
                safe_error = safe_error.replace(supplied_key, "***")
            history.append({"role": "assistant", "content": f"No pude procesarlo: {safe_error}"})
            _, figure = sales_summary([])
            empty_metrics = {"transactions": 0, "units": 0, "currency": "USD", "total": 0.0}
            return (
                history,
                _render_chat(history),
                "Revisa la configuración",
                figure,
                _metric_cards(empty_metrics),
            )

    return app


def main() -> None:
    app = create_app()
    app.run(debug=False)


if __name__ == "__main__":
    main()
