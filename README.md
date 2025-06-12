# Projeto: Otimização de Escalonamento de Atendimentos Psicológicos – Projeto Cuidar Bem

Este projeto propõe uma solução baseada em modelagem matemática para otimizar o escalonamento de atendimentos psicológicos em um centro comunitário, com base no case "Cuidar Bem".

## Contexto

O projeto "Cuidar Bem" visa oferecer atendimento psicológico gratuito a populações em situação de vulnerabilidade social. Com o aumento da demanda e limitações de recursos (salas, profissionais e horários), surgiram desafios na organização das escalas de atendimento, resultando em filas, ociosidade de salas e sobrecarga de profissionais.

## Objetivo

Desenvolver um modelo de Programação Linear Inteira (PLI) que:

* Minimize a quantidade de atendimentos não realizados.
* Equilibre a carga horária entre os profissionais.
* Reduza a subutilização de salas.
* Priorize atendimentos mais urgentes por meio de penalizações diferenciadas.

## Estrutura dos Dados

O modelo utiliza dois arquivos principais no formato CSV:

### 1. `profissionais.csv`

Contém informações sobre cada profissional, incluindo:

* `Profissional`: Nome completo.
* `TiposPrincipais` e `TiposSecundarios`: Tipos de atendimento que o profissional pode realizar.
* `Disponibilidade`: Dias e horários em que o profissional está disponível (ex: "Segunda:8-12;Quarta:13-17").
* `Vinculo`: Categoria (psicólogo, estagiário, assistente).
* `CH_Max`: Carga horária semanal máxima (em horas).

### 2. `demanda.csv`

Contém a demanda prevista por tipo de atendimento:

* `Tipo`: Tipo do atendimento (ex: Urgência, Rotina, Triagem).
* `Dia`, `Hora`: Slot de atendimento.
* `Demanda`: Quantidade de pacientes.
* `Gravidade`: Classificação da urgência (leve, moderado, grave).
* `Duracao`: Tempo estimado (em minutos) para o atendimento.

## Lógica do Modelo

O modelo define variáveis binárias para indicar se um profissional está alocado a um tipo de atendimento em um dado dia e horário. As restrições garantem:

* Alocação só em horários disponíveis.
* Compatibilidade entre profissional e tipo de atendimento.
* Limite de salas ocupadas simultaneamente.
* Respeito à carga horária semanal e diária.
* Priorizacão de urgências por meio de penalidades mais altas em caso de não atendimento.

## Saídas

* `escalonamento.csv`: Resultado do modelo otimizado, com a lista de atendimentos alocados (profissional, dia, hora e tipo).
* `escalonamento_simples.csv`: Resultado de uma solução heurística simples para fins de comparação.

## Como Executar

1. Instale os pacotes necessários:

```bash
pip install pulp pandas
```

2. Garanta que os arquivos `profissionais.csv` e `demanda.csv` estejam na mesma pasta do script.
3. Execute o script Python principal:

```bash
python escalonamento_cuidarbem.py
```

## Observações

* O modelo está preparado para lidar com variações semanais de demanda.
* Pode ser adaptado para incluir novas restrições ou critérios conforme o crescimento do projeto.

## Licença

Uso educacional e comunitário livre, com foco em aplicações sociais na área de saúde mental.
