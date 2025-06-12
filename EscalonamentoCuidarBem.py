# escalonamento_cuidarbem.py

import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, LpInteger, LpBinary, LpContinuous, value

# 1. Parâmetros fixos do modelo
R = 5  # número total de salas disponíveis em cada (dia,hora)
dias_da_semana = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"]
horarios = list(range(8, 18))  # slots 8,9,...,17
alpha = 1e-4  # peso pequeno para balancear carga após minimizar demanda não atendida

# 2. Leitura dos CSVs
df_prof = pd.read_csv("profissionais.csv", dtype=str)
df_dem = pd.read_csv("demanda_semanal.csv", dtype=str)

# --- Processar 'profissionais.csv' ---
# Para cada profissional, precisamos extrair:
#   - Nome (string)
#   - Tipos principais (lista de strings)
#   - Tipos secundários (lista de strings)
#   - Disponibilidade: gerar dicionário a_{p,(d,h)} binário

profissionais = df_prof["Profissional"].tolist()

# Dicionários auxiliares:
TiposPri = {}  # Types prioritários por p
TiposSec = {}  # Types secundários por p
Disponibilidade = {}  # Disponibilidade[p][(d,h)] = 1 ou 0

for idx, linha in df_prof.iterrows():
    p = linha["Profissional"]
    # Extrair listas de tipos
    pri = [t.strip() for t in linha["TiposPrincipais"].split(";") if t.strip()]
    sec = [t.strip() for t in linha["TiposSecundarios"].split(";") if t.strip()]
    TiposPri[p] = set(pri)
    TiposSec[p] = set(sec)

    # Inicializar disponibilidade em zero para todos dias/horários
    Disponibilidade[p] = {}
    for d in dias_da_semana:
        for h in horarios:
            Disponibilidade[p][(d, h)] = 0

    # Processar a string de disponibilidade (ex.: "Segunda:8-12;Quarta:8-18")
    blocos = linha["Disponibilidade"].split(";")
    for bloco in blocos:
        if not bloco.strip():
            continue
        dia, faixa = bloco.split(":")
        dia = dia.strip()
        inicio, fim = faixa.split("-")
        h_inicio = int(inicio)
        h_fim = int(fim)
        # Marcar disponibilidade em todos os horários de h_inicio a h_fim (inclusive)
        for h in range(h_inicio, h_fim + 1):
            if (dia in dias_da_semana) and (h in horarios):
                Disponibilidade[p][(dia, h)] = 1

# Determinar o conjunto de todos os "tipos" que aparecem em demanda
tipos_demanda = sorted(df_dem["Tipo"].unique().tolist())

# Converter demanda para d_{k,(d,h)} (inteiro)
#   Ex.: d[(k,dia,hora)] = valor
from collections import defaultdict
d = defaultdict(int)
for idx, linha in df_dem.iterrows():
    d_dia = linha["Dia"]
    d_hora = int(linha["Hora"])
    d_tipo = linha["Tipo"]
    d_qtd = int(linha["Demanda"])
    d[(d_tipo, d_dia, d_hora)] = d_qtd

# 3. Construção do modelo PuLP
prob = LpProblem("Escalonamento_CuidarBem", LpMinimize)

# 3.1. Variáveis x_{p,(d,h),k} ∈ {0,1}
x = {}
for p in profissionais:
    for d_sem in dias_da_semana:
        for h in horarios:
            if Disponibilidade[p][(d_sem, h)] == 0:
                continue  # profissional não disponível, não criamos variável
            for k in tipos_demanda:
                # Só criamos x[p,d,h,k] se profissional p conhece k (pri ou sec)
                if (k in TiposPri[p]) or (k in TiposSec[p]):
                    x[(p, d_sem, h, k)] = LpVariable(f"x_{p}_{d_sem}_{h}_{k}", cat=LpBinary)
# 3.2. Variáveis u_{k,(d,h)} >= 0 (inteiras) → demanda não atendida
u = {}
for k in tipos_demanda:
    for d_sem in dias_da_semana:
        for h in horarios:
            # Mesmo que a demanda seja zero, criamos a variável para ficar consistente
            u[(k, d_sem, h)] = LpVariable(f"u_{k}_{d_sem}_{h}", lowBound=0, cat=LpInteger)

# 3.3. Variáveis w_p = carga total de p (em horas)
w = {}
for p in profissionais:
    w[p] = LpVariable(f"w_{p}", lowBound=0, cat=LpInteger)

# 3.4. Variável z para a carga máxima
z = LpVariable("z_maxCarga", lowBound=0, cat=LpInteger)

# 4. Função‐objetivo: minimizar (1) soma de u + (2) alpha * (z + soma w_p)
#    - Termo principal: minimizar total de demanda não atendida
obj_u = lpSum([u[(k, d_sem, h)] for k in tipos_demanda for d_sem in dias_da_semana for h in horarios])
obj_balance = z + lpSum([w[p] for p in profissionais])
prob += obj_u + alpha * obj_balance, "Objetivo_principal_red_obras_demanda_balanceada"

# 5. Restrições

# 5.1. Cobertura da demanda: para todo (k,d,h),
#     soma_{p} x[p,d,h,k] + u[k,d,h] = d[(k,d,h)]
for k in tipos_demanda:
    for d_sem in dias_da_semana:
        for h in horarios:
            # Demanda específica (pode ser zero se não existir linha explícita)
            demanda_k = d.get((k, d_sem, h), 0)
            # Somar todos os profissionais p que poderiam ter x[p,d,h,k]
            vars_x = []
            for p in profissionais:
                if (p, d_sem, h, k) in x:
                    vars_x.append(x[(p, d_sem, h, k)])
            # Construir a restrição
            prob += lpSum(vars_x) + u[(k, d_sem, h)] == demanda_k, f"Cobertura_demanda_{k}_{d_sem}_{h}"

# 5.2. Cada profissional p, em cada (d,h), atende no máximo 1 paciente (soma sobre k <= 1)
for p in profissionais:
    for d_sem in dias_da_semana:
        for h in horarios:
            # Selecionar quais variáveis x[p,d,h,k] existem
            vars_pdh = []
            for k in tipos_demanda:
                if (p, d_sem, h, k) in x:
                    vars_pdh.append(x[(p, d_sem, h, k)])
            if vars_pdh:
                prob += lpSum(vars_pdh) <= 1, f"Max1_atendimento_por_slot_{p}_{d_sem}_{h}"

# 5.3. Salas limitadas: em cada (d,h), soma sobre p,k de x[p,d,h,k] <= R
for d_sem in dias_da_semana:
    for h in horarios:
        vars_dh = []
        for p in profissionais:
            for k in tipos_demanda:
                if (p, d_sem, h, k) in x:
                    vars_dh.append(x[(p, d_sem, h, k)])
        if vars_dh:
            prob += lpSum(vars_dh) <= R, f"Limite_salas_{d_sem}_{h}"

# 5.4. Carga diária ≤ 8 para cada profissional p e cada dia d
for p in profissionais:
    for d_sem in dias_da_semana:
        vars_p_dia = []
        for h in horarios:
            for k in tipos_demanda:
                if (p, d_sem, h, k) in x:
                    vars_p_dia.append(x[(p, d_sem, h, k)])
        if vars_p_dia:
            prob += lpSum(vars_p_dia) <= 8, f"Max8h_por_dia_{p}_{d_sem}"

# 5.5. Definição de w_p = soma_{(d,h),k} x[p,d,h,k]
for p in profissionais:
    vars_p_semana = []
    for d_sem in dias_da_semana:
        for h in horarios:
            for k in tipos_demanda:
                if (p, d_sem, h, k) in x:
                    vars_p_semana.append(x[(p, d_sem, h, k)])
    if vars_p_semana:
        prob += w[p] == lpSum(vars_p_semana), f"Def_w_{p}"
    else:
        # Se p não tem horário disponível nenhum, força w[p]=0
        prob += w[p] == 0, f"Def_w_zero_{p}"

# 5.6. z >= w[p] para todo p  (para modelar carga máxima)
for p in profissionais:
    prob += z >= w[p], f"Def_z_ge_w_{p}"

# 6. Resolver o modelo
prob.solve()

print("Status:", LpStatus[prob.status])
print("Objetivo (total demanda não atendida + α·...):", value(prob.objective))

# 7. Montar o DataFrame de alocação para exportar para CSV
#    Queremos colunas: Profissional | Dia | Hora | Tipo
alocacoes = []
for (p, d_sem, h, k), var in x.items():
    if var.value() == 1:  # se escolhido
        alocacoes.append({
            "Profissional": p,
            "Dia": d_sem,
            "Hora": h,
            "Tipo": k
        })

df_aloc = pd.DataFrame(alocacoes)
df_aloc = df_aloc.sort_values(["Dia","Hora","Profissional","Tipo"])

# 8. Exportar para CSV
df_aloc.to_csv("escalonamento.csv", index=False)
print("Arquivo 'escalonamento.csv' gerado com sucesso. Contém as colunas: Profissional, Dia, Hora, Tipo.")
