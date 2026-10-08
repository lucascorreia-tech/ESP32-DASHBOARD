import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ws_manager import get_ws_manager
from kinematics import TrackConfig

st.set_page_config(
    page_title="VeloTrilho • Relatório de Evolução",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-title {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
        color: #1e293b;
        font-size: 2.1rem;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .metric-card-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 6px;
    }
    .metric-val-main {
        font-size: 1.85rem;
        font-weight: 800;
        color: #1e293b;
        line-height: 1.1;
    }
    .metric-val-unit {
        font-size: 0.95rem;
        font-weight: 600;
        color: #64748b;
        margin-left: 3px;
    }
    .metric-badge-green {
        display: inline-block;
        background-color: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .metric-badge-amber {
        display: inline-block;
        background-color: #fffbeb;
        color: #92400e;
        border: 1px solid #fde68a;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .didactic-box {
        background-color: #f8fafc;
        border-left: 4px solid #166534;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 12px 0 20px 0;
        color: #334155;
    }
    .track-container {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 20px;
    }
    .track-rail {
        height: 10px;
        background: linear-gradient(90deg, #94a3b8 0%, #64748b 100%);
        border-radius: 5px;
        position: relative;
        margin: 35px 20px 25px 20px;
    }
    .track-sensor-node {
        position: absolute;
        top: -18px;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background-color: #ffffff;
        border: 3px solid #166534;
        color: #166534;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 0.85rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transform: translateX(-50%);
    }
    .track-label-top {
        position: absolute;
        top: -45px;
        transform: translateX(-50%);
        font-size: 0.8rem;
        font-weight: 700;
        color: #334155;
        white-space: nowrap;
    }
    .track-label-bottom {
        position: absolute;
        top: 30px;
        transform: translateX(-50%);
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
        white-space: nowrap;
    }
    .track-segment-banner {
        position: absolute;
        top: -12px;
        transform: translateX(-50%);
        background-color: #fef3c7;
        border: 1px dashed #d97706;
        color: #92400e;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .status-badge-online {
        background-color: #166534;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .status-badge-warning {
        background-color: #d97706;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .status-badge-offline {
        background-color: #64748b;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Helper to render raw HTML safely
def _html(content: str):
    st.html(content)

ws_mgr = get_ws_manager()

with st.sidebar:
    st.markdown("### 🔌 Conexão WebSocket (ESP32)")
    
    if ws_mgr.status_state == "online":
        st.html('<div class="status-badge-online">● CONECTADO</div>')
    elif ws_mgr.status_state == "warning":
        st.html('<div class="status-badge-warning">▲ AGUARDANDO / CONECTANDO</div>')
    else:
        st.html('<div class="status-badge-offline">○ DESCONECTADO</div>')
        
    st.caption(f"**Status:** {ws_mgr.status_message}")
    st.divider()

    connection_mode = st.radio(
        "Modo de Operação:",
        ["Cliente WS (Conectar ao ESP32)", "Servidor WS (ESP32 conecta ao PC)", "Simulador Virtual (Sem Hardware)"],
        index=0 if ws_mgr.mode == "client" else (1 if ws_mgr.mode == "server" else 0)
    )

    if connection_mode == "Cliente WS (Conectar ao ESP32)":
        ws_url = st.text_input(
            "URL do WebSocket do ESP32:",
            value=ws_mgr.server_url,
            help="IP do ESP32 na rede local ou no SoftAP (ex: ws://192.168.4.1:81)"
        )
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Conectar", use_container_width=True, type="primary"):
                ws_mgr.start_client(ws_url)
                st.rerun()
        with col_c2:
            if st.button("Desconectar", use_container_width=True):
                ws_mgr.stop()
                st.rerun()

    elif connection_mode == "Servidor WS (ESP32 conecta ao PC)":
        server_port = st.number_input("Porta Local do Servidor:", min_value=1024, max_value=65535, value=ws_mgr.server_port)
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("Iniciar Servidor", use_container_width=True, type="primary"):
                ws_mgr.start_server(int(server_port))
                st.rerun()
        with col_s2:
            if st.button("Parar Servidor", use_container_width=True):
                ws_mgr.stop()
                st.rerun()
        st.caption("No código do ESP32, aponte para o IP desta máquina nesta porta.")

    else:
        st.markdown("#### Teste Rápido (Simulador)")
        st.caption("Gera dados de passagem com equações de MRUV e ruído experimental.")
        sim_slope = st.slider("Inclinação Teórica do Trilho (°):", min_value=1.0, max_value=25.0, value=6.0, step=0.5)
        sim_v0 = st.slider("Velocidade Inicial v₀ (m/s):", min_value=0.0, max_value=1.0, value=0.15, step=0.05)
        
        if st.button("▶️ Simular Disparo do Carrinho", use_container_width=True, type="primary"):
            ws_mgr.simulate_single_run(slope_deg=sim_slope, initial_speed=sim_v0)
            st.rerun()

    st.divider()
    st.markdown("### 🕹️ Comandos Remotos (ESP32)")
    if st.button("🔄 Resetar Sensores no ESP32", use_container_width=True):
        ws_mgr.send_command({"command": "reset"})
        st.toast("Comando de reset enviado ao ESP32!")

    with st.expander("Inclinação do Servo SG90 (GPIO 13)"):
        servo_angle = st.slider("Ângulo do Servo (°):", min_value=0, max_value=45, value=0, step=1)
        if st.button("Aplicar Inclinação", use_container_width=True):
            ws_mgr.send_command({"command": "set_servo", "angle": int(servo_angle)})
            st.toast(f"Ângulo {servo_angle}° enviado ao servo!")

    st.divider()
    st.markdown("### 📏 Geometria do Trilho (m)")
    d1_in = st.number_input("Sensor 1 (P1):", value=ws_mgr.track_config.d1, step=0.05, format="%.2f")
    d2_in = st.number_input("Sensor 2 (P2):", value=ws_mgr.track_config.d2, step=0.05, format="%.2f")
    d3_in = st.number_input("Sensor 3 (P3):", value=ws_mgr.track_config.d3, step=0.05, format="%.2f")
    if (d1_in != ws_mgr.track_config.d1 or d2_in != ws_mgr.track_config.d2 or d3_in != ws_mgr.track_config.d3):
        ws_mgr.update_track_config(d1_in, d2_in, d3_in)

    st.divider()
    col_clear, col_refresh = st.columns(2)
    with col_clear:
        if st.button("Limpar Histórico", use_container_width=True):
            ws_mgr.clear_history()
            st.rerun()
    with col_refresh:
        auto_refresh = st.checkbox("Tempo Real", value=True, help="Atualiza a cada 1 segundo para captar novos disparos.")

@st.fragment(run_every="1s" if auto_refresh else None)
def render_live_dashboard():
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.html('<div class="main-title">Trilho de Ar • Relatório de Evolução (VeloTrilho)</div>')
        st.html('<div class="sub-title">Medição cinemática de alta precisão via interrupções de hardware ESP32 e transmissão WebSocket.</div>')
    with header_col2:
        total_runs = len(ws_mgr.history)
        st.metric("Total de Ensaios", f"{total_runs}", delta=f"Último: #{ws_mgr.latest_result.run_id}" if ws_mgr.latest_result else "Aguardando")

    latest = ws_mgr.latest_result
    cfg = ws_mgr.track_config
    ds12 = cfg.delta_s12
    ds23 = cfg.delta_s23
    ds_tot = cfg.delta_s_total

    t1_disp = f"{latest.t1:.4f} s" if latest else "--"
    t2_disp = f"{latest.t2:.4f} s" if latest else "--"
    t3_disp = f"{latest.t3:.4f} s" if latest else "--"

    v12_disp = f"{latest.v12:.3f} m/s" if latest else f"Δs: {ds12:.2f} m"
    v23_disp = f"{latest.v23:.3f} m/s" if latest else f"Δs: {ds23:.2f} m"

    rail_html = f"""
    <div class="track-container">
        <div style="font-weight: 700; color: #334155; margin-bottom: 25px; font-size: 0.95rem;">
            📍 Esquema Didático do Trilho e Posicionamento dos Sensores
        </div>
        <div class="track-rail">
            <div style="position: absolute; left: 5%;">
                <div class="track-label-top">SENSOR 1 (P1)</div>
                <div class="track-sensor-node">S₁</div>
                <div class="track-label-bottom"><b>{cfg.d1:.2f} m</b><br><span style="color:#065f46;">t₁ = {t1_disp}</span></div>
            </div>

            <div style="position: absolute; left: 27.5%;">
                <div class="track-segment-banner">Trecho 1: {v12_disp}</div>
            </div>

            <div style="position: absolute; left: 50%;">
                <div class="track-label-top">SENSOR 2 (P2)</div>
                <div class="track-sensor-node">S₂</div>
                <div class="track-label-bottom"><b>{cfg.d2:.2f} m</b><br><span style="color:#065f46;">t₂ = {t2_disp}</span></div>
            </div>

            <div style="position: absolute; left: 72.5%;">
                <div class="track-segment-banner">Trecho 2: {v23_disp}</div>
            </div>

            <div style="position: absolute; left: 95%;">
                <div class="track-label-top">SENSOR 3 (P3)</div>
                <div class="track-sensor-node">S₃</div>
                <div class="track-label-bottom"><b>{cfg.d3:.2f} m</b><br><span style="color:#065f46;">t₃ = {t3_disp}</span></div>
            </div>
        </div>
        <div style="margin-top: 48px; font-size: 0.8rem; color: #64748b; text-align: right;">
            Distância total calibrada: <b>{ds_tot:.2f} metros</b> | GPIOs: 4 (S₁), 5 (S₂), 18 (S₃) | Inclinação: GPIO 13 (Servo SG90)
        </div>
    </div>
    """
    st.html(rail_html)

    if latest is None:
        st.info(
            "⏳ **Aguardando dados do primeiro ensaio.**\n\n"
            "- Conecte ao seu ESP32 pela barra lateral esquerda (`ws://192.168.4.1:81`), ou\n"
            "- Clique no botão **'▶️ Simular Disparo do Carrinho'** na barra lateral para gerar um ensaio de demonstração agora mesmo!"
        )
    else:
        st.markdown("### 📊 Grandezas Cinemáticas Registradas (Ensaio Atual)")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.html(f"""
            <div class="metric-card">
                <div class="metric-card-header">Trecho 1 (S₁ → S₂)</div>
                <div class="metric-val-main">{latest.v12:.3f}<span class="metric-val-unit">m/s</span></div>
                <div style="margin-top: 6px; font-size: 0.85rem; color: #475569;">
                    <b>Δs₁₂:</b> {ds12:.2f} m<br>
                    <b>Δt₁₂:</b> {latest.dt12:.4f} s
                </div>
                <div class="metric-badge-green">Velocidade Média 1</div>
            </div>
            """)

        with c2:
            st.html(f"""
            <div class="metric-card">
                <div class="metric-card-header">Trecho 2 (S₂ → S₃)</div>
                <div class="metric-val-main">{latest.v23:.3f}<span class="metric-val-unit">m/s</span></div>
                <div style="margin-top: 6px; font-size: 0.85rem; color: #475569;">
                    <b>Δs₂₃:</b> {ds23:.2f} m<br>
                    <b>Δt₂₃:</b> {latest.dt23:.4f} s
                </div>
                <div class="metric-badge-green">Velocidade Média 2</div>
            </div>
            """)

        with c3:
            st.html(f"""
            <div class="metric-card">
                <div class="metric-card-header">Percurso Total (S₁ → S₃)</div>
                <div class="metric-val-main">{latest.v_med:.3f}<span class="metric-val-unit">m/s</span></div>
                <div style="margin-top: 6px; font-size: 0.85rem; color: #475569;">
                    <b>Δs Total:</b> {ds_tot:.2f} m<br>
                    <b>Δt Total:</b> {latest.dt_total:.4f} s
                </div>
                <div class="metric-badge-amber">Velocidade Média Global</div>
            </div>
            """)

        with c4:
            st.html(f"""
            <div class="metric-card">
                <div class="metric-card-header">Aceleração Experimental</div>
                <div class="metric-val-main">{latest.acceleration:.3f}<span class="metric-val-unit">m/s²</span></div>
                <div style="margin-top: 6px; font-size: 0.85rem; color: #475569;">
                    <b>Variação (Δv):</b> {latest.speed_delta_pct:+.1f}%<br>
                    <b>Comportamento:</b> {latest.motion_type.split()[0]}
                </div>
                <div class="metric-badge-amber">{latest.motion_type}</div>
            </div>
            """)

        st.markdown("### 🧮 Memorial de Cálculo Didático (Passo a Passo)")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.html('<div class="didactic-box" style="padding:14px 18px;">')
            st.markdown(
                f"**1. Velocidade no Trecho 1** ($S_1 \\to S_2$):  \n"
                f"$$v_{{12}} = \\frac{{{cfg.d2:.3f} - {cfg.d1:.3f}}}{{{latest.dt12:.4f}}} "
                f"= \\mathbf{{{latest.v12:.3f}\\;\\text{{m/s}}}}$$\n\n"
                f"**2. Velocidade no Trecho 2** ($S_2 \\to S_3$):  \n"
                f"$$v_{{23}} = \\frac{{{cfg.d3:.3f} - {cfg.d2:.3f}}}{{{latest.dt23:.4f}}} "
                f"= \\mathbf{{{latest.v23:.3f}\\;\\text{{m/s}}}}$$"
            )

        with col_m2:
            dt_mid = (latest.dt12 + latest.dt23) / 2.0
            st.html('<div class="didactic-box" style="padding:14px 18px;">')
            st.markdown(
                f"**3. Velocidade Média Global** ($S_1 \\to S_3$):  \n"
                f"$$v_{{\\text{{méd}}}} = \\frac{{{cfg.d3:.3f} - {cfg.d1:.3f}}}{{{latest.dt_total:.4f}}} "
                f"= \\mathbf{{{latest.v_med:.3f}\\;\\text{{m/s}}}}$$\n\n"
                f"**4. Aceleração Média Estimada** ($a_m$):  \n"
                f"$$a_m = \\frac{{{latest.v23:.3f} - {latest.v12:.3f}}}{{{dt_mid:.4f}}} "
                f"= \\mathbf{{{latest.acceleration:.3f}\\;\\text{{m/s}}^2}}$$"
            )

        st.markdown("### 📈 Análise Gráfica Experimental")
        g1, g2 = st.columns(2)

        with g1:
            t_vals = [0.0, latest.dt12, latest.dt_total]
            s_vals = [cfg.d1, cfg.d2, cfg.d3]

            fig_st = go.Figure()

            fig_st.add_trace(go.Scatter(
                x=t_vals,
                y=s_vals,
                mode='markers+text',
                name='Sensores (Medições)',
                text=[f'P1 ({s_vals[0]:.2f}m)', f'P2 ({s_vals[1]:.2f}m)', f'P3 ({s_vals[2]:.2f}m)'],
                textposition='top left',
                marker=dict(size=14, color='#166534', symbol='diamond', line=dict(width=2, color='#0f172a'))
            ))

            t_dense = np.linspace(0.0, max(0.001, latest.dt_total), 50)
            v0_est = max(0.0, latest.v12 - 0.5 * latest.acceleration * latest.dt12)
            s_dense = cfg.d1 + v0_est * t_dense + 0.5 * latest.acceleration * (t_dense ** 2)

            fig_st.add_trace(go.Scatter(
                x=t_dense,
                y=s_dense,
                mode='lines',
                name='Modelo Físico s(t)',
                line=dict(color='#d97706', width=3, dash='dot')
            ))

            fig_st.update_layout(
                title=dict(text="<b>Posição vs. Tempo [s × t]</b>", font=dict(color='#1e293b', size=15)),
                xaxis=dict(title="Tempo decorrido a partir de S₁ (s)", gridcolor='#e2e8f0', zeroline=True),
                yaxis=dict(title="Posição no trilho (m)", gridcolor='#e2e8f0', zeroline=True),
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                margin=dict(l=40, r=20, t=40, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_st, use_container_width=True)

        with g2:
            trechos = ["Trecho 1 (S₁→S₂)", "Trecho 2 (S₂→S₃)", "Média Geral"]
            v_bars = [latest.v12, latest.v23, latest.v_med]
            cores_bar = ['#166534', '#047857', '#d97706']

            fig_v = go.Figure()
            fig_v.add_trace(go.Bar(
                x=trechos,
                y=v_bars,
                text=[f"{v:.3f} m/s" for v in v_bars],
                textposition='auto',
                marker=dict(color=cores_bar, line=dict(color='#1e293b', width=1.5)),
                width=0.45
            ))

            fig_v.update_layout(
                title=dict(text="<b>Velocidades Escalares Médias Calculadas</b>", font=dict(color='#1e293b', size=15)),
                xaxis=dict(title="Intervalo Analisado", gridcolor='#e2e8f0'),
                yaxis=dict(title="Velocidade (m/s)", gridcolor='#e2e8f0', zeroline=True),
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                margin=dict(l=40, r=20, t=40, b=40)
            )
            st.plotly_chart(fig_v, use_container_width=True)

        st.markdown("### 📋 Histórico de Ensaios Realizados (Tabela para Relatório)")
        history_records = [res.to_dict() for res in ws_mgr.history]
        df_history = pd.DataFrame(history_records)

        if not df_history.empty:
            st.dataframe(df_history, use_container_width=True, hide_index=True)
            csv_data = df_history.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(
                label="📥 Baixar Dados em CSV (Pronto para Excel e Relatório)",
                data=csv_data,
                file_name="dados_velotrilho_relatorio.csv",
                mime="text/csv",
                type="primary"
            )

    st.markdown("---")
    tab_teoria, tab_ws_log, tab_hardware = st.tabs([
        "📚 Fundamentação Física & Fórmulas",
        "📡 Monitor de Pacotes WebSocket",
        "⚙️ Esquema de Ligação ESP32"
    ])

    with tab_teoria:
        st.markdown(r"""
        #### Formulação Cinemática Aplicada

        1. **Intervalo de Tempo ($\Delta t$):**
           Calculado com precisão de microssegundos no ESP32 através de interrupções de hardware:
           $$\Delta t_{12} = T_2 - T_1 \quad , \quad \Delta t_{23} = T_3 - T_2 \quad , \quad \Delta t_{total} = T_3 - T_1$$

        2. **Velocidade Escalar Média ($v_m$):**
           Razão entre o deslocamento entre os sensores e o intervalo de tempo medido:
           $$v_{12} = \frac{S_2 - S_1}{\Delta t_{12}} \quad , \quad v_{23} = \frac{S_3 - S_2}{\Delta t_{23}} \quad , \quad v_{total} = \frac{S_3 - S_1}{\Delta t_{total}}$$

        3. **Aceleração Escalar Média ($a_m$):**
           Variação da velocidade entre os centros temporais dos dois trechos:
           $$a_m = \frac{v_{23} - v_{12}}{\frac{\Delta t_{12} + \Delta t_{23}}{2}}$$

        - Se $a_m \approx 0$ e $v_{12} \approx v_{23}$, o movimento se classifica como **Movimento Retilíneo Uniforme (MRU)**.
        - Se $a_m > 0$ e constante (trilho com inclinação fixada pelo servo SG90), temos **Movimento Retilíneo Uniformemente Variado (MRUV)** acelerado.
        """)

    with tab_ws_log:
        st.markdown("#### Mensagens Brutas e Diagnóstico do WebSocket")
        st.caption("Últimos eventos, pacotes JSON recebidos e comandos enviados ao ESP32:")
        logs = list(ws_mgr.raw_logs)
        if logs:
            st.code("\n".join(logs[-15:]), language="text")
        else:
            st.info("Nenhuma mensagem registrada até o momento.")

    with tab_hardware:
        st.markdown("""
        #### Pinagem do Hardware Utilizada
        - **Sensor 1 (P1):** Pino `GPIO 4` (Interrupção em `FALLING`, Pull-up interno)
        - **Sensor 2 (P2):** Pino `GPIO 5` (Interrupção em `FALLING`, Pull-up interno)
        - **Sensor 3 (P3):** Pino `GPIO 18` (Interrupção em `FALLING`, Pull-up interno)
        - **Servo SG90 (Inclinação):** Pino `GPIO 13` (Controlável pelo slider na barra lateral)
        - **Firmware:** Arquivo `firmware_esp32_websocket.ino` pronto na pasta raiz do projeto.
        """)

render_live_dashboard()
