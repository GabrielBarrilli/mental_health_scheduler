# escalonamento_cuidarbem.py (com solução ótima e simples)

import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, LpInteger, LpBinary, value
from collections import defaultdict

# 1. parâmetros fixos do modelo
R = 5
dias_da_semana = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"]
horarios = list(range(8, 18))
alpha = 1e-4

# 2. leitura dos CSVs
df_prof = pd.read_csv("profissionais.csv", dtype=str)
df_dem = pd.read_csv("demanda_semanal.csv", dtype=str)

profissionais = df_prof["Profissional"].tolist()
TiposPri, TiposSec, Disponibilidade = {}, {}, {}

for _, linha in df_prof.iterrows():
    p = linha["Profissional"]
    TiposPri[p] = set(t.strip() for t in linha["TiposPrincipais"].split(";") if t.strip())
    TiposSec[p] = set(t.strip() for t in linha["TiposSecundarios"].split(";") if t.strip())
    Disponibilidade[p] = {(d, h): 0 for d in dias_da_semana for h in horarios}
    for bloco in linha["Disponibilidade"].split(";"):
        if not bloco.strip(): continue
        dia, faixa = bloco.split(":")
        inicio, fim = map(int, faixa.split("-"))
        for h in range(inicio, fim + 1):
            if dia in dias_da_semana and h in horarios:
                Disponibilidade[p][(dia, h)] = 1

tipos_demanda = sorted(df_dem["Tipo"].unique().tolist())
d = defaultdict(int)
for _, linha in df_dem.iterrows():
    d[(linha["Tipo"], linha["Dia"], int(linha["Hora"]))] = int(linha["Demanda"])

# 3. modelo otimizado (original)
prob = LpProblem("Escalonamento_CuidarBem", LpMinimize)
x, u = {}, {}
for p in profissionais:
    for d_sem in dias_da_semana:
        for h in horarios:
            if Disponibilidade[p][(d_sem, h)] == 0: continue
            for k in tipos_demanda:
                if k in TiposPri[p] or k in TiposSec[p]:
                    x[(p, d_sem, h, k)] = LpVariable(f"x_{p}_{d_sem}_{h}_{k}", cat=LpBinary)

for k in tipos_demanda:
    for d_sem in dias_da_semana:
        for h in horarios:
            u[(k, d_sem, h)] = LpVariable(f"u_{k}_{d_sem}_{h}", lowBound=0, cat=LpInteger)

w, z = {}, LpVariable("z_maxCarga", lowBound=0, cat=LpInteger)
for p in profissionais:
    w[p] = LpVariable(f"w_{p}", lowBound=0, cat=LpInteger)

obj_u = lpSum([u[(k, d_sem, h)] for k in tipos_demanda for d_sem in dias_da_semana for h in horarios])
obj_balance = z + lpSum([w[p] for p in profissionais])
prob += obj_u + alpha * obj_balance

for k in tipos_demanda:
    for d_sem in dias_da_semana:
        for h in horarios:
            vars_x = [x[(p, d_sem, h, k)] for p in profissionais if (p, d_sem, h, k) in x]
            prob += lpSum(vars_x) + u[(k, d_sem, h)] == d[(k, d_sem, h)], f"Cobertura_{k}_{d_sem}_{h}"

for p in profissionais:
    for d_sem in dias_da_semana:
        for h in horarios:
            vars_pdh = [x[(p, d_sem, h, k)] for k in tipos_demanda if (p, d_sem, h, k) in x]
            if vars_pdh:
                prob += lpSum(vars_pdh) <= 1

for d_sem in dias_da_semana:
    for h in horarios:
        prob += lpSum([x[(p, d_sem, h, k)] for p in profissionais for k in tipos_demanda if (p, d_sem, h, k) in x]) <= R

for p in profissionais:
    for d_sem in dias_da_semana:
        prob += lpSum([x[(p, d_sem, h, k)] for h in horarios for k in tipos_demanda if (p, d_sem, h, k) in x]) <= 8

for p in profissionais:
    prob += w[p] == lpSum([x[(p, d_sem, h, k)] for d_sem in dias_da_semana for h in horarios for k in tipos_demanda if (p, d_sem, h, k) in x])
    prob += z >= w[p]

prob.solve()

print("Status (ótimo):", LpStatus[prob.status])
print("Objetivo (ótimo):", value(prob.objective))

aloc_otima = []
for (p, d_sem, h, k), var in x.items():
    if var.value() == 1:
        aloc_otima.append({"Profissional": p, "Dia": d_sem, "Hora": h, "Tipo": k})

pd.DataFrame(aloc_otima).sort_values(["Dia","Hora","Profissional","Tipo"]).to_csv("escalonamento.csv", index=False)
print("Arquivo 'escalonamento.csv' gerado com sucesso.")

# 4. solução simples (heurística)
aloc_simples = []
ocupado = defaultdict(bool)

for (tipo, dia, hora), demanda in sorted(d.items()):
    for _ in range(demanda):
        alocado = False
        for p in profissionais:
            if not ocupado[(p, dia, hora)] and Disponibilidade[p][(dia, hora)] == 1 and (tipo in TiposPri[p] or tipo in TiposSec[p]):
                aloc_simples.append({"Profissional": p, "Dia": dia, "Hora": hora, "Tipo": tipo})
                ocupado[(p, dia, hora)] = True
                alocado = True
                break
        if not alocado:
            continue  # demanda não atendida

pd.DataFrame(aloc_simples).sort_values(["Dia", "Hora", "Profissional", "Tipo"]).to_csv("escalonamento_simples.csv", index=False)
print("Arquivo 'escalonamento_simples.csv' gerado com sucesso.")
