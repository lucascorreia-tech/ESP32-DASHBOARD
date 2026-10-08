# Relatório de Evolução
## **Resumo do que foi desenvolvido**  
Foi projetada e validada a arquitetura lógica e o firmware embarcado em C/C++ do sistema VeloTrilho. Foi implementada a leitura de sinais por interrupções de hardware com precisão de microssegundos (`micros()`) para cálculo de velocidade (MRU) e aceleração (MRUV), controle de inclinação por servo motor e simulação de tração por drive de motor.
## Hardware montado até o momento
Foi feito através de Prototipagem Virtual, montando o circuto no ambiente simulado contendo o ESP32 DevKit V1, 3 cahves de acionamento por interrupção (simulando os sensores IR de barreira), 1 Servo Motor SG90 no GPIO 13 (inclinação).
## Sensores utilizados e teste realizados
Os sensores IR de barreira (GPIOs 4, 5 e 18) foram configurados com resistores internos de pull-up e rotinas de interrupção em borda de descida (FALLING). Os teste feitos foram testes de lógicas de tempo, onde simulamos disparos sequenciais das rotinas de serviço de interrupção para capturar os instantes  $T_1$ ,
$T_2$, $T_3$ e cálculo dos intervalos de tempo ($\Delta t$)

## Código desenvolvido no ESP32
Firmware compilado com sucesso na Arduino IDE v2 (uso de 21% da memória Flash e 6% da RAM do ESP32 Dev Module).
![[WhatsApp Image 2026-09-16 at 13.49.15.jpeg]]
## Descrição da lógica do programa
O programa utiliza interrupções por hardware para capturar o instante exato em que a barreira do sensor é interrompida. Com base em distâncias fixas no trilho 
($d = 0,50 m$), o algoritmo calcula:

- **Velocidade Escalar Média (MRU)**: $v = \frac{\Delta x}{\Delta t}$
- **Aceleração Média (MRUV)**: $a = \frac{\Delta v}{\Delta t}$ no trecho subsequente com inclinação.
- **Saída de Dados**: Formatação e transmissão contínua das métricas via Monitor Serial
## Evidências dos testes
![[Pasted image 20260916142957.png]]![[WhatsApp Image 2026-09-16 at 13.45.57.jpeg]]
## Resultado Obtidos
Validação estática do código C++ sem erros de sintaxe ou estouro de memória no ESP32 e Comprovação matemática do algoritmo de letirua temporal e cálculo cinemático.
## Problemas encontrados
Indisponibilidade de teste de hardware pela ferramenta online, pelo grande volume de acessos.
## Como a equipe resolveu ou pretende resolver
A resolução é da compra do hardware físico para teste e validação do projeto.