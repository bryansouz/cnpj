import streamlit as st
import pandas as pd
import sqlite3
import datetime
import os
import hashlib
import json
from datetime import datetime, timedelta
import time

# Configuração de desenvolvimento
DEV_MODE = True  # Altere para False em produção

# Configuração da página
st.set_page_config(
    page_title="Sistema de Cobrança para Treinadores",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do banco de dados
def init_db():
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    # Criar tabela de treinadores
    c.execute('''
    CREATE TABLE IF NOT EXISTS treinadores (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL
    )
    ''')
    
    # Criar tabela de alunos
    c.execute('''
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone TEXT NOT NULL,
        data_inicio TEXT NOT NULL,
        data_pagamento TEXT NOT NULL,
        dia_vencimento INTEGER,
        valor_mensalidade REAL NOT NULL,
        treinador_id INTEGER NOT NULL,
        FOREIGN KEY (treinador_id) REFERENCES treinadores (id)
    )
    ''')
    
    # Verificar se a coluna dia_vencimento existe, se não existir, adicioná-la
    try:
        c.execute('SELECT dia_vencimento FROM alunos LIMIT 1')
    except sqlite3.OperationalError:
        # A coluna não existe, adicioná-la e preencher com o dia da data_pagamento
        c.execute('ALTER TABLE alunos ADD COLUMN dia_vencimento INTEGER')
        # Preencher a coluna dia_vencimento com o dia da data_pagamento para registros existentes
        c.execute('UPDATE alunos SET dia_vencimento = CAST(substr(data_pagamento, 9, 2) AS INTEGER)')
    
    # Criar tabela de pagamentos
    c.execute('''
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY,
        data_vencimento TEXT NOT NULL,
        data_pagamento TEXT,
        valor REAL NOT NULL,
        status TEXT NOT NULL,
        aluno_id INTEGER NOT NULL,
        FOREIGN KEY (aluno_id) REFERENCES alunos (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Funções de autenticação
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed_password):
    return hash_password(password) == hashed_password

def register_user(nome, email, senha):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    try:
        hashed_password = hash_password(senha)
        c.execute("INSERT INTO treinadores (nome, email, senha) VALUES (?, ?, ?)", 
                 (nome, email, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(email, senha):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    c.execute("SELECT id, nome, email, senha FROM treinadores WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password(senha, user[3]):
        return {"id": user[0], "nome": user[1], "email": user[2]}
    return None

# Funções para gerenciar alunos
def adicionar_aluno(nome, email, telefone, data_pagamento, valor_mensalidade, treinador_id):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    data_inicio = datetime.now().strftime("%Y-%m-%d")
    
    # Extrair o dia do mês da data de pagamento para o dia fixo de vencimento
    data_vencimento = datetime.strptime(data_pagamento, "%Y-%m-%d")
    dia_vencimento = data_vencimento.day
    
    c.execute('''
    INSERT INTO alunos (nome, email, telefone, data_inicio, data_pagamento, dia_vencimento, valor_mensalidade, treinador_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nome, email, telefone, data_inicio, data_pagamento, dia_vencimento, valor_mensalidade, treinador_id))
    
    aluno_id = c.lastrowid
    
    # Criar o primeiro pagamento
    c.execute('''
    INSERT INTO pagamentos (data_vencimento, valor, status, aluno_id)
    VALUES (?, ?, ?, ?)
    ''', (data_pagamento, valor_mensalidade, "Pendente", aluno_id))
    
    conn.commit()
    conn.close()
    return aluno_id

def adicionar_aluno_com_status(nome, email, telefone, data_pagamento, valor_mensalidade, treinador_id, status_inicial="Pendente"):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    data_inicio = datetime.now().strftime("%Y-%m-%d")
    
    # Extrair o dia do mês da data de pagamento para o dia fixo de vencimento
    data_vencimento = datetime.strptime(data_pagamento, "%Y-%m-%d")
    dia_vencimento = data_vencimento.day
    
    c.execute('''
    INSERT INTO alunos (nome, email, telefone, data_inicio, data_pagamento, dia_vencimento, valor_mensalidade, treinador_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nome, email, telefone, data_inicio, data_pagamento, dia_vencimento, valor_mensalidade, treinador_id))
    
    aluno_id = c.lastrowid
    
    # Criar o primeiro pagamento com o status especificado
    # A data de vencimento u00e9 a data informada pelo usuu00e1rio
    
    # Se o status for "Pago", registramos a data de pagamento efetivo
    data_pagamento_efetivo = None
    if status_inicial == "Pago":
        data_pagamento_efetivo = datetime.now().strftime("%Y-%m-%d")
    
    c.execute('''
    INSERT INTO pagamentos (data_vencimento, data_pagamento, valor, status, aluno_id)
    VALUES (?, ?, ?, ?, ?)
    ''', (data_pagamento, data_pagamento_efetivo, valor_mensalidade, status_inicial, aluno_id))
    
    conn.commit()
    conn.close()
    return aluno_id

def listar_alunos(treinador_id):
    conn = sqlite3.connect('academia.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
    SELECT * FROM alunos WHERE treinador_id = ? ORDER BY nome
    ''', (treinador_id,))
    
    alunos = [dict(row) for row in c.fetchall()]
    conn.close()
    return alunos

def obter_status_pagamento(aluno_id):
    conn = sqlite3.connect('academia.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
    SELECT * FROM pagamentos WHERE aluno_id = ? ORDER BY data_vencimento DESC LIMIT 1
    ''', (aluno_id,))
    
    pagamento = c.fetchone()
    conn.close()
    
    if pagamento:
        return dict(pagamento)
    return None

def registrar_pagamento(pagamento_id):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    data_atual = datetime.now().strftime("%Y-%m-%d")
    c.execute('''
    UPDATE pagamentos SET data_pagamento = ?, status = 'Pago' WHERE id = ?
    ''', (data_atual, pagamento_id))
    
    conn.commit()
    conn.close()

def criar_proximo_pagamento(aluno_id, valor, data_ultimo_pagamento):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    # Obter o dia de vencimento fixo do aluno
    c.execute('SELECT dia_vencimento FROM alunos WHERE id = ?', (aluno_id,))
    resultado = c.fetchone()
    
    if resultado is None or resultado[0] is None:
        # Se não houver dia de vencimento definido, usar a data do último pagamento
        data_vencimento = datetime.strptime(data_ultimo_pagamento, "%Y-%m-%d")
        dia_vencimento = data_vencimento.day
    else:
        dia_vencimento = resultado[0]
        # Converter a data do último pagamento para extrair apenas mês e ano
        data_vencimento = datetime.strptime(data_ultimo_pagamento, "%Y-%m-%d")
    
    # Calcular a próxima data de vencimento (mês seguinte, mesmo dia do vencimento)
    mes_seguinte = data_vencimento.month + 1
    ano = data_vencimento.year
    
    # Ajustar se estivermos passando para o próximo ano
    if mes_seguinte > 12:
        mes_seguinte = 1
        ano += 1
    
    # Lidar com datas inválidas (ex: dia 31 em meses com menos dias)
    ultimo_dia = 31  # Valor padrão alto
    if mes_seguinte in [4, 6, 9, 11]:  # Meses com 30 dias
        ultimo_dia = 30
    elif mes_seguinte == 2:  # Fevereiro
        if (ano % 4 == 0 and ano % 100 != 0) or (ano % 400 == 0):  # Ano bissexto
            ultimo_dia = 29
        else:
            ultimo_dia = 28
    
    # Usar o menor valor entre o dia de vencimento e o último dia do mês seguinte
    dia = min(dia_vencimento, ultimo_dia)
    
    # Criar a nova data de vencimento
    nova_data_vencimento = datetime(ano, mes_seguinte, dia)
    data_vencimento_str = nova_data_vencimento.strftime("%Y-%m-%d")
    
    # Inserir o novo pagamento no banco de dados
    c.execute('''
    INSERT INTO pagamentos (data_vencimento, data_pagamento, valor, status, aluno_id)
    VALUES (?, NULL, ?, 'Pendente', ?)
    ''', (data_vencimento_str, valor, aluno_id))
    
    conn.commit()
    conn.close()

def alterar_status_pagamento(pagamento_id, novo_status):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    # Se o status for alterado para "Pago", registramos a data de pagamento
    if novo_status == "Pago":
        data_atual = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
        UPDATE pagamentos SET status = ?, data_pagamento = ? WHERE id = ?
        ''', (novo_status, data_atual, pagamento_id))
    else:
        # Se for alterado para outro status, removemos a data de pagamento
        c.execute('''
        UPDATE pagamentos SET status = ?, data_pagamento = NULL WHERE id = ?
        ''', (novo_status, pagamento_id))
    
    conn.commit()
    conn.close()

def atualizar_aluno(aluno_id, nome, email, telefone, data_pagamento, valor_mensalidade):
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    
    # Extrair o dia do mês da data de pagamento para o dia fixo de vencimento
    data_vencimento = datetime.strptime(data_pagamento, "%Y-%m-%d")
    dia_vencimento = data_vencimento.day
    
    c.execute('''
    UPDATE alunos 
    SET nome = ?, email = ?, telefone = ?, data_pagamento = ?, dia_vencimento = ?, valor_mensalidade = ?
    WHERE id = ?
    ''', (nome, email, telefone, data_pagamento, dia_vencimento, valor_mensalidade, aluno_id))
    
    # Verificar se a atualização foi bem-sucedida
    if c.rowcount > 0:
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

# Função para verificar pagamentos e gerar notificações
def verificar_pagamentos():
    conn = sqlite3.connect('academia.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    hoje = datetime.now().date()
    tres_dias_depois = (hoje + timedelta(days=3)).strftime("%Y-%m-%d")
    hoje_str = hoje.strftime("%Y-%m-%d")
    
    # Pagamentos que vencem em 3 dias
    c.execute('''
    SELECT p.id, p.data_vencimento, p.valor, a.nome, a.email, a.telefone
    FROM pagamentos p
    JOIN alunos a ON p.aluno_id = a.id
    WHERE p.status = 'Pendente' AND p.data_vencimento = ?
    ''', (tres_dias_depois,))
    
    notificacoes_3_dias = [dict(row) for row in c.fetchall()]
    
    # Pagamentos que vencem hoje
    c.execute('''
    SELECT p.id, p.data_vencimento, p.valor, a.nome, a.email, a.telefone
    FROM pagamentos p
    JOIN alunos a ON p.aluno_id = a.id
    WHERE p.status = 'Pendente' AND p.data_vencimento = ?
    ''', (hoje_str,))
    
    notificacoes_hoje = [dict(row) for row in c.fetchall()]
    
    # Pagamentos atrasados
    c.execute('''
    SELECT p.id, p.data_vencimento, p.valor, a.nome, a.email, a.telefone
    FROM pagamentos p
    JOIN alunos a ON p.aluno_id = a.id
    WHERE p.status = 'Pendente' AND p.data_vencimento < ?
    ''', (hoje_str,))
    
    notificacoes_atrasadas = [dict(row) for row in c.fetchall()]
    
    # Atualizar status dos pagamentos atrasados
    c.execute('''
    UPDATE pagamentos SET status = 'Atrasado' 
    WHERE status = 'Pendente' AND data_vencimento < ?
    ''', (hoje_str,))
    
    conn.commit()
    conn.close()
    
    return {
        "tres_dias": notificacoes_3_dias,
        "hoje": notificacoes_hoje,
        "atrasados": notificacoes_atrasadas
    }

# Inicializar o banco de dados
init_db()

# Inicializar sessão
if 'logged_in' not in st.session_state:
    # Em modo de desenvolvimento, podemos iniciar já logado
    st.session_state.logged_in = DEV_MODE

if 'user' not in st.session_state:
    if DEV_MODE:
        # Usuário padrão para desenvolvimento
        st.session_state.user = {"id": 1, "nome": "Desenvolvedor", "email": "dev@exemplo.com"}
    else:
        st.session_state.user = None

# Sidebar para navegação
def sidebar():
    with st.sidebar:
        st.image("https://img.freepik.com/vetores-premium/logotipo-de-fitness-com-haltere_23-2147495393.jpg", width=200)
        
        # Verificar se o usuário está logado
        if 'user' in st.session_state and st.session_state.user is not None:
            st.title(f"Olá, {st.session_state.user['nome']}!")
            
            # Verificar primeiro se o usuário selecionou manualmente uma opção
            # Menu de navegação
            selected = st.radio(
                "Navegação",
                ["Dashboard", "Cadastrar Aluno", "Notificações", "Configurações", "Sair"]
            )
            
            # Se o usuário fez uma seleção manual, ela tem prioridade
            if 'ultimo_radio_selecionado' in st.session_state and selected != st.session_state.ultimo_radio_selecionado:
                pagina = selected
                # Se o usuário navega manualmente, limpar a página especial
                if 'pagina' in st.session_state and st.session_state.pagina == "Editar Aluno":
                    st.session_state.pagina = None
            # Caso contrário, verificar se há uma página especial (como editar aluno)
            elif 'pagina' in st.session_state and st.session_state.pagina is not None:
                pagina = st.session_state.pagina
            else:
                # Se não há página especial, usar a seleção atual
                pagina = selected
            
            # Armazenar a última seleção para comparação na próxima execução
            st.session_state.ultimo_radio_selecionado = selected
            
            # Tratar o botão de sair
            if pagina == "Sair":
                st.session_state.user = None
                st.session_state.pagina = "Login"
                pagina = "Login"
        else:
            # Se o usuário não estiver logado, mostrar apenas o título
            st.title("Sistema de Cobrança")
            pagina = "Login"
        
        return pagina

# Páginas do aplicativo
def pagina_login():
    st.title("Sistema de Cobrança para Treinadores")
    
    # Limpar qualquer mensagem de erro anterior
    if 'login_error' in st.session_state:
        st.error(st.session_state.login_error)
        del st.session_state.login_error
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        
        if st.button("Entrar"):
            if not email or not senha:
                st.error("Preencha todos os campos!")
            else:
                user = authenticate_user(email, senha)
                if user:
                    # Inicializar corretamente a sessão
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success("Login realizado com sucesso!")
                    # Pequeno atraso para garantir que o usuário veja a mensagem de sucesso
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("Email ou senha incorretos!")
    
    with tab2:
        st.subheader("Cadastro de Novo Treinador")
        nome = st.text_input("Nome completo", key="reg_nome")
        email = st.text_input("Email", key="reg_email")
        senha = st.text_input("Senha", type="password", key="reg_senha")
        senha2 = st.text_input("Confirme a senha", type="password", key="reg_senha2")
        
        if st.button("Cadastrar"):
            if senha != senha2:
                st.error("As senhas não coincidem!")
            elif not nome or not email or not senha:
                st.error("Todos os campos são obrigatórios!")
            else:
                if register_user(nome, email, senha):
                    st.success("Cadastro realizado com sucesso! Faça login para continuar.")
                    # Limpar os campos após o cadastro
                    st.session_state.reg_nome = ""
                    st.session_state.reg_email = ""
                    st.session_state.reg_senha = ""
                    st.session_state.reg_senha2 = ""
                else:
                    st.error("Erro ao cadastrar. Este email já pode estar em uso.")

def pagina_dashboard():
    st.title("Dashboard")
    
    # Verificar se o usuário está logado
    if 'user' not in st.session_state or st.session_state.user is None:
        st.error("Você precisa estar logado para acessar o dashboard.")
        if st.button("Ir para o Login"):
            st.session_state.pagina = "Login"
            st.experimental_rerun()
        return
        
    # Estabelecer conexão com o banco de dados
    conn = sqlite3.connect('academia.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Verificar se há um pagamento registrado recentemente
    if 'ultimo_pagamento_registrado' in st.session_state:
        aluno_id = st.session_state.ultimo_pagamento_registrado['aluno_id']
        valor = st.session_state.ultimo_pagamento_registrado['valor']
        data_vencimento = st.session_state.ultimo_pagamento_registrado['data_vencimento']
        
        st.success("Pagamento registrado com sucesso!")
        st.info("Deseja criar o próximo pagamento mensal para este aluno?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sim, criar próximo pagamento"):
                criar_proximo_pagamento(aluno_id, valor, data_vencimento)
                st.success("Próximo pagamento mensal criado com sucesso!")
                del st.session_state.ultimo_pagamento_registrado
                st.experimental_rerun()
        with col2:
            if st.button("Não, apenas registrar este pagamento"):
                del st.session_state.ultimo_pagamento_registrado
                st.experimental_rerun()
        
        # Parar a execução do dashboard até que o usuário decida
        return
    
    # Obter lista de alunos do treinador
    alunos = listar_alunos(st.session_state.user['id'])
    
    # Estatísticas
    col1, col2, col3, col4 = st.columns(4)
    
    total_alunos = len(alunos)
    
    # Calcular pagamentos pendentes, atrasados e pagos
    pagamentos_pendentes = 0
    pagamentos_atrasados = 0
    pagamentos_pagos = 0
    receita_mensal = 0
    receita_recebida = 0
    
    for aluno in alunos:
        receita_mensal += aluno['valor_mensalidade']
        status = obter_status_pagamento(aluno['id'])
        if status:
            if status['status'] == 'Pendente':
                pagamentos_pendentes += 1
            elif status['status'] == 'Atrasado':
                pagamentos_atrasados += 1
            elif status['status'] == 'Pago':
                pagamentos_pagos += 1
                receita_recebida += status['valor']
    
    with col1:
        st.metric("Total de Alunos", total_alunos)
    
    with col2:
        st.metric("Pagamentos Pendentes", pagamentos_pendentes)
        
    with col3:
        st.metric("Pagamentos Atrasados", pagamentos_atrasados, delta=-pagamentos_atrasados, delta_color="inverse")
    
    with col4:
        st.metric("Pagamentos Recebidos", pagamentos_pagos, delta=pagamentos_pagos)
    
    # Adicionar gráfico de receita
    st.subheader("Receita")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Receita Mensal Esperada", f"R$ {receita_mensal:.2f}")
    with col2:
        st.metric("Receita Recebida", f"R$ {receita_recebida:.2f}", 
                 delta=f"R$ {receita_recebida - receita_mensal:.2f}" if receita_mensal > 0 else None)
    
    # Lista de alunos com filtro por status
    st.subheader("Seus Alunos")
    
    if alunos:
        # Adicionar filtro por status
        filtro_status = st.radio(
            "Filtrar por status:",
            ["Todos", "Pendentes", "Atrasados", "Pagos"],
            horizontal=True
        )
        
        # Preparar dados para a tabela
        dados_tabela = []
        for aluno in alunos:
            status_pagamento = obter_status_pagamento(aluno['id'])
            status = status_pagamento['status'] if status_pagamento else "N/A"
            
            # Aplicar filtro
            if filtro_status == "Pendentes" and status != "Pendente":
                continue
            elif filtro_status == "Atrasados" and status != "Atrasado":
                continue
            elif filtro_status == "Pagos" and status != "Pago":
                continue
            
            # Formatar data para exibição
            data_pagamento = datetime.strptime(aluno['data_pagamento'], "%Y-%m-%d").strftime("%d/%m/%Y")
            
            # Calcular dias até o vencimento ou dias de atraso
            dias_info = ""
            if status_pagamento:
                data_venc = datetime.strptime(status_pagamento['data_vencimento'], "%Y-%m-%d").date()
                hoje = datetime.now().date()
                dias_diff = (data_venc - hoje).days
                
                if status == "Pendente":
                    if dias_diff > 0:
                        dias_info = f"Vence em {dias_diff} dias"
                    elif dias_diff == 0:
                        dias_info = "Vence hoje"
                elif status == "Atrasado":
                    dias_info = f"Atrasado há {abs(dias_diff)} dias"
                elif status == "Pago":
                    if status_pagamento['data_pagamento']:
                        data_pag = datetime.strptime(status_pagamento['data_pagamento'], "%Y-%m-%d").date()
    
    # 2. Lista de Alunos com Status de Pagamento
    st.subheader('Alunos e Status de Pagamento')
    
    # Tabs para filtrar por status
    tabs = st.tabs(["Todos", "Pendentes", "Pagos", "Atrasados"])
    
    # Preparar os dados dos alunos e seus pagamentos para exibição
    alunos_com_pagamentos = []
    for aluno in alunos:
        c.execute('''
        SELECT p.* FROM pagamentos p
        WHERE p.aluno_id = ?
        ORDER BY p.data_vencimento DESC LIMIT 1
        ''', (aluno['id'],))
        ultimo_pagamento = c.fetchone()
        
        if ultimo_pagamento:
            aluno_info = dict(aluno)
            aluno_info['pagamento'] = dict(ultimo_pagamento)
            alunos_com_pagamentos.append(aluno_info)
    
    # Função auxiliar para exibir os cards de alunos
    def exibir_cards_alunos(alunos_filtrados, aba_id):
        if not alunos_filtrados:
            st.info(f"Nenhum aluno encontrado com este status.")
            return
            
        st.markdown("<style>"
                  ".status-card {padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}"
                  ".status-pendente {border-left: 5px solid orange;}"
                  ".status-pago {border-left: 5px solid green;}"
                  ".status-atrasado {border-left: 5px solid red;}"
                  "</style>", unsafe_allow_html=True)
        
        for i, aluno_info in enumerate(alunos_filtrados):
            pagamento = aluno_info['pagamento']
            status_class = f"status-{pagamento['status'].lower()}"
            
            # Criar um identificador único para cada card
            card_id = f"{aba_id}_{aluno_info['id']}_{i}_{pagamento['status'].lower()}"
            
            st.markdown(f"<div class='status-card {status_class}'>"
                      f"<h4>{aluno_info['nome']}</h4>"
                      f"<div style='display:flex;justify-content:space-between;'>"
                      f"<div><strong>Telefone:</strong> {aluno_info['telefone']}</div>"
                      f"<div><strong>Dia de Vencimento:</strong> Dia {aluno_info['dia_vencimento']}</div>"
                      f"</div>"
                      f"<div style='display:flex;justify-content:space-between;'>"
                      f"<div><strong>Vencimento Atual:</strong> {pagamento['data_vencimento']}</div>"
                      f"<div><strong>Valor:</strong> R$ {aluno_info['valor_mensalidade']:.2f}</div>"
                      f"</div>"
                      f"<div style='display:flex;justify-content:space-between;align-items:center;margin-top:10px;'>"
                      f"<div><span style='font-weight:bold;color:"
                      f"{"green" if pagamento['status'] == "Pago" else "orange" if pagamento['status'] == "Pendente" else "red"};'>"
                      f"Status: {pagamento['status']}</span>"
                      f"{f" (Pago em: {pagamento['data_pagamento']})" if pagamento['status'] == "Pago" and pagamento['data_pagamento'] else ""}"
                      f"</div>"
                      f"<div>"
                      f"<a href='#'>Detalhes</a> | "
                      f"<a href='#'>Editar</a>"
                      f"</div>"
                      f"</div>"
                      f"</div>", unsafe_allow_html=True)
            
            # Usar unique keys para botões com uma combinação verdadeiramente única
            col1, col2, col3 = st.columns(3)
            
            # IDs de botões únicos por aba, posição na lista e ação
            detalhe_key = f"detalhe_{aba_id}_{i}_{aluno_info['id']}_{pagamento['status'].lower()}"
            editar_key = f"editar_{aba_id}_{i}_{aluno_info['id']}_{pagamento['status'].lower()}"
            pago_key = f"pago_{aba_id}_{i}_{aluno_info['id']}_{pagamento['status'].lower()}"
            
            if st.button(f"Ver Detalhes", key=detalhe_key):
                # Armazenar o ID do aluno para mostrar detalhes
                st.session_state.aluno_detalhes = aluno_info['id']
                # Aqui você poderia mostrar um modal com detalhes do histórico de pagamentos
                st.markdown("### Histórico de Pagamentos")
                c.execute('''
                SELECT p.* FROM pagamentos p
                WHERE p.aluno_id = ?
                ORDER BY p.data_vencimento DESC
                LIMIT 6
                ''', (aluno_info['id'],))
                historico = [dict(row) for row in c.fetchall()]
                
                if historico:
                    for pgto in historico:
                        cor_status = "green" if pgto['status'] == "Pago" else "orange" if pgto['status'] == "Pendente" else "red"
                        st.markdown(f"<div style='padding:8px;margin-bottom:5px;border-left:3px solid {cor_status};'>"
                                  f"<div><strong>Vencimento:</strong> {pgto['data_vencimento']}</div>"
                                  f"<div><strong>Status:</strong> <span style='color:{cor_status}'>{pgto['status']}</span></div>"
                                  f"{f"<div><strong>Data do Pagamento:</strong> {pgto['data_pagamento']}</div>" if pgto['data_pagamento'] else ""}"
                                  f"<div><strong>Valor:</strong> R$ {pgto['valor']:.2f}</div>"
                                  f"</div>", unsafe_allow_html=True)
                else:
                    st.info("Sem histórico de pagamentos disponível.")
            
            if st.button(f"Editar", key=editar_key):
                st.session_state.aluno_a_editar = aluno_info['id']
                st.session_state.pagina = "Editar Aluno"
                st.experimental_rerun()
            
            if pagamento['status'] != "Pago" and st.button(f"Marcar como Pago", key=pago_key):
                alterar_status_pagamento(pagamento['id'], "Pago")
                
                # Armazenar informações para criar o próximo pagamento
                st.session_state.ultimo_pagamento_registrado = {
                    'aluno_id': aluno_info['id'],
                    'valor': pagamento['valor'],
                    'data_vencimento': pagamento['data_vencimento']
                }
                
                st.success(f"Pagamento de {aluno_info['nome']} registrado com sucesso!")
                st.experimental_rerun()
    
    # Exibir alunos em cada aba
    with tabs[0]:  # Todos os alunos
        if not alunos_com_pagamentos:
            st.info("Nenhum aluno cadastrado. Adicione alunos na aba 'Cadastrar Aluno'.")
        else:
            exibir_cards_alunos(alunos_com_pagamentos, "todos")
    
    with tabs[1]:  # Alunos com pagamentos pendentes
        alunos_pendentes = [a for a in alunos_com_pagamentos if a['pagamento']['status'] == "Pendente"]
        exibir_cards_alunos(alunos_pendentes, "pendentes")
    
    with tabs[2]:  # Alunos com pagamentos pagos
        alunos_pagos = [a for a in alunos_com_pagamentos if a['pagamento']['status'] == "Pago"]
        exibir_cards_alunos(alunos_pagos, "pagos")
    
    with tabs[3]:  # Alunos com pagamentos atrasados
        alunos_atrasados = [a for a in alunos_com_pagamentos if a['pagamento']['status'] == "Atrasado"]
        exibir_cards_alunos(alunos_atrasados, "atrasados")

def pagina_cadastro_aluno():
    st.title("Cadastrar Novo Aluno")
    
    # Verificar se o usuário está logado
    if 'user' not in st.session_state or st.session_state.user is None:
        st.error("Você precisa estar logado para cadastrar um aluno.")
        if st.button("Ir para o Login"):
            st.session_state.pagina = "Login"
            st.experimental_rerun()
        return
    
    # Informações sobre o sistema de pagamento com data de vencimento fixa
    st.info("ℹ️ O sistema usa um dia fixo de vencimento mensal. A data que você selecionar abaixo definirá o dia de vencimento que será mantido para todos os meses futuros deste aluno (por exemplo, dia 10 de cada mês).")
    
    with st.form("form_cadastro_aluno"):
        nome = st.text_input("Nome Completo")
        email = st.text_input("Email")
        telefone = st.text_input("Telefone")
        
        col1, col2 = st.columns(2)
        with col1:
            # Explicação clara sobre a data de vencimento
            data_pagamento = st.date_input("Data do Primeiro Vencimento", 
                                          value=datetime.now().date(),
                                          help="Esta data define o dia de vencimento mensal para este aluno. Por exemplo, se você selecionar o dia 15, os pagamentos futuros sempre vencerão no dia 15 de cada mês.")
            
            dia_selecionado = data_pagamento.day
            st.caption(f"O dia {dia_selecionado} será fixado como dia de vencimento mensal")
            
        with col2:
            valor_mensalidade = st.number_input("Valor da Mensalidade (R$)", 
                                               min_value=0.0, 
                                               step=10.0,
                                               format="%.2f")
        
        # Adicionando campo para status inicial do pagamento
        status_inicial = st.selectbox("Status inicial do pagamento", 
                                      options=["Pendente", "Pago", "Atrasado"],
                                      help="Se marcar como 'Pago', o sistema registrará automaticamente a data de pagamento atual e criará o próximo pagamento para o mês seguinte com status 'Pendente'.")
        
        submitted = st.form_submit_button("Cadastrar Aluno")
        
        if submitted:
            if not nome or not email or not telefone or not valor_mensalidade:
                st.error("Todos os campos são obrigatórios!")
            else:
                try:
                    data_pagamento_str = data_pagamento.strftime("%Y-%m-%d")
                    
                    # Chamando função modificada para adicionar aluno com status inicial
                    aluno_id = adicionar_aluno_com_status(nome, email, telefone, data_pagamento_str, 
                                             valor_mensalidade, st.session_state.user['id'], status_inicial)
                    if aluno_id:
                        st.success(f"Aluno {nome} cadastrado com sucesso!")
                        st.balloons()
                        # Redirecionar para o dashboard após o cadastro
                        st.session_state.pagina = "Dashboard"
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar aluno: {str(e)}")
                    st.error("Verifique se você está logado corretamente.")

def pagina_notificacoes():
    st.title("Notificações de Pagamento")
    
    # Verificar se o usuário está logado
    if 'user' not in st.session_state or st.session_state.user is None:
        st.error("Você precisa estar logado para acessar as notificações.")
        if st.button("Ir para o Login"):
            st.session_state.pagina = "Login"
            st.experimental_rerun()
        return
    
    try:
        # Verificar pagamentos e gerar notificações
        notificacoes = verificar_pagamentos()
        
        tab1, tab2, tab3 = st.tabs(["Vencimentos em 3 dias", "Vencimentos Hoje", "Pagamentos Atrasados"])
        
        with tab1:
            if notificacoes["tres_dias"]:
                for notif in notificacoes["tres_dias"]:
                    with st.expander(f"{notif['nome']} - Vence em 3 dias"):
                        st.write(f"**Valor:** R$ {notif['valor']:.2f}")
                        st.write(f"**Data de Vencimento:** {datetime.strptime(notif['data_vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
                        st.write(f"**Contato:** {notif['email']} | {notif['telefone']}")
                        
                        mensagem = f"Olá {notif['nome']}, este é um lembrete de que sua mensalidade no valor de R$ {notif['valor']:.2f} vence em 3 dias ({datetime.strptime(notif['data_vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}). Obrigado!"
                        st.text_area("Mensagem para enviar", mensagem, key=f"msg_3d_{notif['id']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Enviar Email", key=f"email_3d_{notif['id']}"):
                                st.success("Simulação: Email enviado com sucesso!")
                        with col2:
                            if st.button("Enviar WhatsApp", key=f"whats_3d_{notif['id']}"):
                                st.success("Simulação: Mensagem de WhatsApp enviada com sucesso!")
            else:
                st.info("Não há pagamentos vencendo em 3 dias.")
        
        with tab2:
            if notificacoes["hoje"]:
                for notif in notificacoes["hoje"]:
                    with st.expander(f"{notif['nome']} - Vence hoje"):
                        st.write(f"**Valor:** R$ {notif['valor']:.2f}")
                        st.write(f"**Data de Vencimento:** {datetime.strptime(notif['data_vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
                        st.write(f"**Contato:** {notif['email']} | {notif['telefone']}")
                        
                        mensagem = f"Olá {notif['nome']}, sua mensalidade no valor de R$ {notif['valor']:.2f} vence hoje ({datetime.strptime(notif['data_vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}). Por favor, realize o pagamento. Obrigado!"
                        st.text_area("Mensagem para enviar", mensagem, key=f"msg_h_{notif['id']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Enviar Email", key=f"email_h_{notif['id']}"):
                                st.success("Simulação: Email enviado com sucesso!")
                        with col2:
                            if st.button("Enviar WhatsApp", key=f"whats_h_{notif['id']}"):
                                st.success("Simulação: Mensagem de WhatsApp enviada com sucesso!")
            else:
                st.info("Não há pagamentos vencendo hoje.")
        
        with tab3:
            if notificacoes["atrasados"]:
                for notif in notificacoes["atrasados"]:
                    with st.expander(f"{notif['nome']} - ATRASADO"):
                        st.write(f"**Valor:** R$ {notif['valor']:.2f}")
                        st.write(f"**Data de Vencimento:** {datetime.strptime(notif['data_vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
                        st.write(f"**Contato:** {notif['email']} | {notif['telefone']}")
                        
                        dias_atraso = notif['dias_atraso']
                        mensagem = f"Olá {notif['nome']}, sua mensalidade no valor de R$ {notif['valor']:.2f} está atrasada há {dias_atraso} dias. Por favor, entre em contato para regularizar sua situação. Obrigado!"
                        st.text_area("Mensagem para enviar", mensagem, key=f"msg_a_{notif['id']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Enviar Email", key=f"email_a_{notif['id']}"):
                                st.success("Simulação: Email enviado com sucesso!")
                        with col2:
                            if st.button("Enviar WhatsApp", key=f"whats_a_{notif['id']}"):
                                st.success("Simulação: Mensagem de WhatsApp enviada com sucesso!")
            else:
                st.info("Não há pagamentos atrasados.")
    except Exception as e:
        st.error(f"Erro ao carregar notificações: {str(e)}")
        st.error("Tente novamente ou contate o suporte.")

def pagina_configuracoes():
    st.title("Configurações")
    
    st.subheader("Dados do Treinador")
    
    # Obter dados atuais do usuário
    conn = sqlite3.connect('academia.db')
    c = conn.cursor()
    c.execute("SELECT nome, email FROM treinadores WHERE id = ?", (st.session_state.user['id'],))
    treinador = c.fetchone()
    conn.close()
    
    if treinador:
        with st.form("form_config_treinador"):
            nome = st.text_input("Nome", value=treinador[0])
            email = st.text_input("Email", value=treinador[1], disabled=True)
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha = st.text_input("Nova Senha (deixe em branco para manter a atual)", type="password")
            
            submitted = st.form_submit_button("Atualizar Dados")
            
            if submitted:
                if senha_atual:
                    # Verificar senha atual
                    conn = sqlite3.connect('academia.db')
                    c = conn.cursor()
                    c.execute("SELECT senha FROM treinadores WHERE id = ?", (st.session_state.user['id'],))
                    senha_hash = c.fetchone()[0]
                    
                    if check_password(senha_atual, senha_hash):
                        # Atualizar dados
                        if nova_senha:
                            nova_senha_hash = hash_password(nova_senha)
                            c.execute("UPDATE treinadores SET nome = ?, senha = ? WHERE id = ?", 
                                     (nome, nova_senha_hash, st.session_state.user['id']))
                        else:
                            c.execute("UPDATE treinadores SET nome = ? WHERE id = ?", 
                                     (nome, st.session_state.user['id']))
                        
                        conn.commit()
                        st.success("Dados atualizados com sucesso!")
                        
                        # Atualizar sessão
                        st.session_state.user['nome'] = nome
                    else:
                        st.error("Senha atual incorreta!")
                    
                    conn.close()
                else:
                    st.error("Digite sua senha atual para confirmar as alterações.")
    
    st.subheader("Configurações de Notificação")
    st.info("Em uma versão futura, você poderá configurar modelos de mensagens e integrações com serviços de email e WhatsApp.")

def pagina_editar_aluno():
    st.title("Editar Aluno")
    
    # Verificar se o usuário está logado
    if 'user' not in st.session_state or st.session_state.user is None:
        st.error("Você precisa estar logado para editar um aluno.")
        if st.button("Ir para o Login"):
            st.session_state.pagina = "Login"
            st.experimental_rerun()
        return
    
    if 'editando_aluno' not in st.session_state:
        st.error("Nenhum aluno selecionado para edição.")
        if st.button("Voltar para o Dashboard"):
            st.session_state.pagina = "Dashboard"
            st.experimental_rerun()
        return
    
    aluno = st.session_state.editando_aluno
    
    with st.form("form_editar_aluno"):
        nome = st.text_input("Nome Completo", value=aluno['nome'])
        email = st.text_input("Email", value=aluno['email'])
        telefone = st.text_input("Telefone", value=aluno['telefone'])
        
        col1, col2 = st.columns(2)
        with col1:
            # Converter a data de string para objeto date
            data_atual = datetime.strptime(aluno['data_pagamento'], "%Y-%m-%d").date()
            data_pagamento = st.date_input("Data de Pagamento Mensal", value=data_atual)
        with col2:
            valor_mensalidade = st.number_input("Valor da Mensalidade (R$)", 
                                              min_value=0.0, 
                                              value=float(aluno['valor_mensalidade']),
                                              step=10.0,
                                              format="%.2f")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Salvar Alterações")
        with col2:
            cancelar = st.form_submit_button("Cancelar")
        
        if cancelar:
            # Limpar o aluno em edição e voltar para o dashboard
            del st.session_state.editando_aluno
            st.session_state.pagina = "Dashboard"
            st.experimental_rerun()
        
        if submitted:
            if not nome or not email or not telefone or not valor_mensalidade:
                st.error("Todos os campos são obrigatórios!")
            else:
                try:
                    data_pagamento_str = data_pagamento.strftime("%Y-%m-%d")
                    
                    # Atualizar dados do aluno
                    sucesso = atualizar_aluno(aluno['id'], nome, email, telefone, 
                                             data_pagamento_str, valor_mensalidade)
                    
                    if sucesso:
                        st.success(f"Dados do aluno {nome} atualizados com sucesso!")
                        # Limpar o aluno em edição e voltar para o dashboard
                        del st.session_state.editando_aluno
                        st.session_state.pagina = "Dashboard"
                        st.experimental_rerun()
                    else:
                        st.error("Erro ao atualizar os dados do aluno.")
                except Exception as e:
                    st.error(f"Erro ao atualizar aluno: {str(e)}")
                    st.error("Verifique se você está logado corretamente.")

# Aplicativo principal
def main():
    # Verificar pagamentos
    verificar_pagamentos()
    
    # Mostrar página correspondente
    if not st.session_state.logged_in:
        pagina_login()
    else:
        # Se estiver no modo de desenvolvimento, mostrar um indicador
        if DEV_MODE:
            st.sidebar.warning("MODO DE DESENVOLVIMENTO - Login automático")
        
        pagina = sidebar()
        
        if pagina == "Dashboard":
            pagina_dashboard()
        elif pagina == "Cadastrar Aluno":
            pagina_cadastro_aluno()
        elif pagina == "Notificações":
            pagina_notificacoes()
        elif pagina == "Configurações":
            pagina_configuracoes()
        elif pagina == "Editar Aluno" and 'aluno_id' in st.session_state:
            pagina_editar_aluno()

if __name__ == "__main__":
    main()