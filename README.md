# ⏱️ VeloTrilho • Relatório de Evolução (Dashboard Streamlit + ESP32 WebSocket)

Este projeto implementa a interface gráfica em tempo real para a conclusão da etapa **"Relatório de Evolução"** do sistema **VeloTrilho** (trilho de ar / plano inclinado com 3 sensores ópticos de barreira controlados por um ESP32 DevKit V1).

O dashboard exibe em tempo real as **três distâncias instantâneas**, os **instantes e intervalos de tempo**, as **velocidades médias em cada trecho** e a **aceleração calculada**, com suporte nativo a **WebSocket** e um simulador virtual para testes sem o hardware físico.

---

## 📂 Estrutura dos Arquivos Criados

| Arquivo | Descrição |
| :--- | :--- |
| **[`app.py`](app.py)** | Aplicação principal em Streamlit com design didático, memorial de cálculo passo a passo, controle remoto de inclinação do servo (GPIO 13), diagrama do trilho, gráficos Plotly e exportação para CSV. |
| **[`ws_manager.py`](ws_manager.py)** | Gerenciador assíncrono de WebSocket (*thread-safe*), suportando conexão cliente ao ESP32, envio de comandos (reset e inclinação de servo), servidor local no PC e modo simulador. |
| **[`kinematics.py`](kinematics.py)** | Motor de cálculos cinemáticos (MRU e MRUV), conversão de microssegundos para segundos, cálculo de $\Delta t$, $v_m$, aceleração e diagnóstico de movimento. |
| **[`firmware_esp32_websocket.ino`](firmware_esp32_websocket.ino)** | Firmware em C++ pronto para gravar no ESP32, com interrupções em `FALLING`, captura via `micros()`, controle do servo SG90 no GPIO 13, servidor WebSocket na porta `81` e montagem do pacote JSON. |
| **[`requirements.txt`](requirements.txt)** | Lista de dependências Python necessárias para o projeto. |
| **[`README.md`](README.md)** | Este guia completo de instalação, execução, configuração e testes. |

---

## 🎨 Design e Paleta Visual

Conforme especificado no projeto, o design foi elaborado de forma **simples, didática e sem o uso das cores padrões de IA (sem tons predominantes de roxo e azul)**:
- **Verde Mata / Esmeralda (`#166534`)**: Destaque positivo, status "Conectado", nós dos sensores e velocidade do primeiro trecho.
- **Âmbar Industrial (`#d97706`)**: Alertas, segundo trecho, velocidade média global e modelo cinemático $s(t)$.
- **Grafite / Cinza Técnico (`#1e293b` / `#475569`)**: Tipografia de alta legibilidade, régua do trilho e contornos.
- **Branco Neve / Off-White (`#ffffff` / `#f8fafc`)**: Fundo dos cartões e áreas de leitura didática.

---

## 🚀 Como Executar o Dashboard (Passo a Passo)

### 1. Pré-requisitos
- **Python 3.10 ou superior** instalado no computador.
- Ambiente virtual `.venv` já configurado na pasta do projeto.

### 2. Ativar o Ambiente Virtual
Abra o terminal do Windows PowerShell na pasta `C:\Users\NTSTI\Desktop\Streamlit` e execute:

```powershell
.\.venv\Scripts\Activate.ps1
```

*(Se as dependências ainda não estiverem instaladas, execute: `pip install -r requirements.txt`)*

### 3. Iniciar a Aplicação Streamlit
Com o ambiente ativado, execute:

```powershell
streamlit run app.py
```
*(Ou diretamente pelo executável do ambiente virtual: `.\.venv\Scripts\streamlit.exe run app.py`)*

O Streamlit iniciará o servidor local e abrirá automaticamente no seu navegador padrão no endereço:
```text
http://localhost:8501
```

---

## 🔌 Conexão com o ESP32 via WebSocket

### 1. Pinagem do Hardware (ESP32 DevKit V1)
Conforme documentado no relatório técnico:
- **Sensor 1 (Ponto Inicial $P_1$):** Pino `GPIO 4` (Interrupção em `FALLING` com Pull-up interno)
- **Sensor 2 (Ponto Médio $P_2$):** Pino `GPIO 5` (Interrupção em `FALLING` com Pull-up interno)
- **Sensor 3 (Ponto Final $P_3$):** Pino `GPIO 18` (Interrupção em `FALLING` com Pull-up interno)
- **Servo Motor SG90 (Inclinação):** Pino `GPIO 13`

### 2. Gravação do Firmware no ESP32
1. Abra a **Arduino IDE v2**.
2. Abra o arquivo [`firmware_esp32_websocket.ino`](firmware_esp32_websocket.ino).
3. Instale as bibliotecas necessárias no Gerenciador de Bibliotecas da Arduino IDE (`Ctrl + Shift + I`):
   - **`WebSockets`** (por *Markus Sattler*)
   - **`ArduinoJson`** (por *Benoît Blanchon*, versão 6 ou 7)
4. Selecione a placa **ESP32 Dev Module** e a porta COM correspondente.
5. Clique em **Upload (Carregar)**.

### 3. Modos de Conexão Wi-Fi do ESP32

#### Opção A: Modo Ponto de Acesso (SoftAP) — *Recomendado / Padrão*
O ESP32 cria sua própria rede Wi-Fi independente (sem precisar do roteador da sua casa):
1. No firmware, mantenha `const bool USE_ACCESS_POINT = true;`.
2. O ESP32 criará a rede Wi-Fi:
   - **SSID:** `VeloTrilho_ESP32`
   - **Senha:** `12345678`
3. Conecte o Wi-Fi do seu notebook a essa rede `VeloTrilho_ESP32`.
4. O IP padrão do ESP32 é: `192.168.4.1`.
5. No dashboard Streamlit, na barra lateral:
   - Selecione **"Cliente WS (Conectar ao ESP32)"**.
   - Digite no campo de URL: `ws://192.168.4.1:81`.
   - Clique em **"Conectar"**.

#### Opção B: Modo Rede Local (Wi-Fi Doméstico/Laboratório)
1. No firmware, altere `const bool USE_ACCESS_POINT = false;`.
2. Configure o nome e a senha da sua rede:
   ```cpp
   const char* WIFI_SSID = "NOME_DO_SEU_WIFI";
   const char* WIFI_PASS = "SENHA_DO_SEU_WIFI";
   ```
3. Abra o **Monitor Serial** da Arduino IDE em `115200 baud` para ver o IP fornecido pelo roteador (ex: `192.168.1.105`).
4. No Streamlit, aponte a URL para: `ws://192.168.1.105:81` e clique em **"Conectar"**.

---

## 🧪 Teste Imediato Sem Hardware (Simulador Virtual)

Caso você queira testar ou demonstrar o dashboard antes de ligar o ESP32 físico:
1. Abra a barra lateral esquerda do Streamlit.
2. Em **"Modo de Operação"**, selecione: **"Simulador Virtual (Sem Hardware)"**.
3. Ajuste se desejar a inclinação simulada do trilho (ex: `6.0°`) e a velocidade inicial $v_0$ (ex: `0.15 m/s`).
4. Clique no botão **"▶️ Simular Disparo do Carrinho"**.
5. O dashboard gerará instantaneamente um ensaio completo baseado nas equações reais de MRUV com ruído experimental, atualizando as métricas, os gráficos e a tabela histórica.

---

## 📊 Grandezas Cinemáticas Calculadas e Exibidas

Para cada disparo do carrinho ao cruzar os 3 sensores:

1. **Posições dos Sensores:**
   - $S_1 = 0,00\text{ m}$
   - $S_2 = 0,50\text{ m}$
   - $S_3 = 1,00\text{ m}$ *(configuráveis na barra lateral)*
2. **Tempos de Passagem:**
   - $T_1$, $T_2$ e $T_3$ capturados com precisão de microssegundos (`micros()`) nas interrupções de hardware do ESP32.
3. **Intervalos de Tempo:**
   - Trecho 1: $\Delta t_{12} = T_2 - T_1$
   - Trecho 2: $\Delta t_{23} = T_3 - T_2$
   - Percurso Total: $\Delta t_{\text{total}} = T_3 - T_1$
4. **Velocidades Escalares Médias:**
   - Trecho 1 ($S_1 \to S_2$): $v_{12} = \frac{S_2 - S_1}{\Delta t_{12}}$
   - Trecho 2 ($S_2 \to S_3$): $v_{23} = \frac{S_3 - S_2}{\Delta t_{23}}$
   - Velocidade Média Global ($S_1 \to S_3$): $v_{\text{méd}} = \frac{S_3 - S_1}{\Delta t_{\text{total}}}$
5. **Aceleração Escalar Média ($a_m$):**
   $$a_m = \frac{v_{23} - v_{12}}{\frac{\Delta t_{12} + \Delta t_{23}}{2}}$$
6. **Classificação do Movimento:**
   - $\text{MRU}$ (se $|v_{23} - v_{12}| < 3\%$)
   - $\text{MRUV Acelerado}$ (descida ou tração positiva)
   - $\text{MRUV Retardado}$ (atrito excessivo ou subida)

---

## 📋 Exportação para o Relatório Acadêmico

Todos os ensaios realizados ficam registrados na tabela **"Histórico de Ensaios Realizados"**.
- Ao clicar no botão **"📥 Baixar Dados em CSV (Pronto para Excel e Relatório)"**, o sistema exporta um arquivo `.csv` codificado em UTF-8 com separador `;`, pronto para abrir diretamente no Excel, Google Planilhas ou importar em artigos e relatórios LaTeX/Markdown.
