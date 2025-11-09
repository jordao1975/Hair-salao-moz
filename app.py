from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import sqlite3
import os
from datetime import datetime
import shutil
from data_structures import LinkedList, FIFOSort
from dotenv import load_dotenv
from init_db import init_db

init_db()
# 🔹 Inicializar conexão PostgreSQL
init_app(app)

# 🔹 Criar as tabelas no banco PostgreSQL
with app.app_context():
    db.create_all()
app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY', 'troque_esta_chave_por_uma_segura')
DB_PATH = os.getenv('DB_PATH', 'clientes_hair_salon.db')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id_, username, role):
        self.id = id_
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, username, role FROM usuarios WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return User(row['id'], row['username'], row['role'])

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def build_fifo_queue(rows):
    """Constrói fila FIFO (primeiro a chegar, primeiro a ser atendido)"""
    fila = LinkedList()
    
    for r in rows:
        fila.append(
            r['id'],
            r['nome'],
            r['telefone'],
            r['servico_id'],
            r['created_at']
        )
    
    fila_ordenada = FIFOSort.sort_linked_list(fila)
    return fila_ordenada

def average_wait_seconds():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT entrada, chamada FROM atendimentos WHERE entrada IS NOT NULL AND chamada IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    deltas = []
    for r in rows:
        try:
            entrada = datetime.strptime(r['entrada'], '%Y-%m-%d %H:%M:%S')
            chamada = datetime.strptime(r['chamada'], '%Y-%m-%d %H:%M:%S')
            deltas.append((chamada - entrada).total_seconds())
        except Exception:
            pass
    if not deltas:
        return None
    return sum(deltas) / len(deltas)

@app.route('/')
def index():
    avg = average_wait_seconds()
    avg_min = round(avg/60, 1) if avg else None
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as c FROM clientes')
    total = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) as c FROM atendimentos')
    atendidos = cur.fetchone()['c']
    
    cur.execute('''
        SELECT COUNT(*) as c FROM clientes c
        LEFT JOIN (
            SELECT cliente_id, MAX(id) as ultimo FROM atendimentos GROUP BY cliente_id
        ) a ON a.cliente_id = c.id
        WHERE a.ultimo IS NULL
    ''')
    espera = cur.fetchone()['c']
    conn.close()
    
    return render_template('index.html', total=total, atendidos=atendidos, espera=espera, avg_min=avg_min)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, username, role, password FROM usuarios WHERE username = ?', (username,))
        row = cur.fetchone()
        conn.close()
        if row and row['password'] == password:
            user = User(row['id'], row['username'], row['role'])
            login_user(user)
            flash('Login efetuado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada', 'info')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET','POST'])
@login_required
def add():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, nome, preco, duracao_estimada FROM servicos')
    servicos = cur.fetchall()
    conn.close()
    
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form.get('telefone') or None
        servico = request.form.get('servico') or None
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO clientes (nome, telefone, servico_id) VALUES (?,?,?)',
                    (nome, telefone, servico))
        conn.commit()
        conn.close()
        flash('Cliente adicionado à fila com sucesso!', 'success')
        return redirect(url_for('list_clientes'))
    return render_template('add.html', servicos=servicos)

@app.route('/list')
@login_required
def list_clientes():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT c.id, c.nome, c.telefone, c.created_at, 
               s.nome as servico, s.preco, s.duracao_estimada
        FROM clientes c 
        LEFT JOIN servicos s ON c.servico_id = s.id
        ORDER BY c.created_at ASC
    ''')
    clientes = cur.fetchall()
    conn.close()
    return render_template('list.html', clientes=clientes)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cliente(id):
    conn = get_conn()
    cur = conn.cursor()
    
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form.get('telefone') or None
        servico = request.form.get('servico') or None
        
        cur.execute('UPDATE clientes SET nome=?, telefone=?, servico_id=? WHERE id=?',
                    (nome, telefone, servico, id))
        conn.commit()
        conn.close()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('list_clientes'))
    
    cur.execute('SELECT * FROM clientes WHERE id = ?', (id,))
    cliente = cur.fetchone()
    cur.execute('SELECT id, nome, preco FROM servicos')
    servicos = cur.fetchall()
    conn.close()
    
    return render_template('edit.html', cliente=cliente, servicos=servicos)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_cliente(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DELETE FROM clientes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Cliente removido', 'warning')
    return redirect(url_for('list_clientes'))

@app.route('/next', methods=['POST'])
@login_required
def chamar_proximo():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT c.id, c.nome, c.telefone, c.created_at, c.servico_id
        FROM clientes c
        LEFT JOIN (
            SELECT cliente_id, MAX(id) as ultimo FROM atendimentos GROUP BY cliente_id
        ) a ON a.cliente_id = c.id
        LEFT JOIN atendimentos att ON att.id = a.ultimo
        WHERE a.ultimo IS NULL
    ''')
    rows = cur.fetchall()
    
    if not rows:
        conn.close()
        return jsonify({'status': 'empty'}), 200

    fila = build_fifo_queue(rows)
    
    primeiro = fila.remove_head()
    
    if not primeiro:
        conn.close()
        return jsonify({'status': 'empty'}), 200

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('INSERT INTO atendimentos (cliente_id, entrada, chamada, servico_id) VALUES (?,?,?,?)',
                (primeiro.cliente_id, now, now, primeiro.servico_id))
    conn.commit()
    conn.close()

    return jsonify({'status': 'ok', 'cliente': {'id': primeiro.cliente_id, 'nome': primeiro.nome, 'telefone': primeiro.telefone}})

@app.route('/finish/<int:atendimento_id>', methods=['POST'])
@login_required
def finish_atendimento(atendimento_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    valor_pago = request.form.get('valor_pago')
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT entrada FROM atendimentos WHERE id = ?', (atendimento_id,))
    row = cur.fetchone()
    
    if not row:
        conn.close()
        flash('Atendimento não encontrado', 'danger')
        return redirect(url_for('atendimento_atual'))
    
    try:
        entrada = datetime.strptime(row['entrada'], '%Y-%m-%d %H:%M:%S')
        saida_dt = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
        tempo = int((saida_dt - entrada).total_seconds())
    except Exception:
        tempo = None
    
    if valor_pago:
        cur.execute('UPDATE atendimentos SET saida = ?, tempo_atendimento = ?, valor_pago = ? WHERE id = ?', 
                    (now, tempo, float(valor_pago), atendimento_id))
    else:
        cur.execute('UPDATE atendimentos SET saida = ?, tempo_atendimento = ? WHERE id = ?', 
                    (now, tempo, atendimento_id))
    
    conn.commit()
    conn.close()
    flash('Atendimento finalizado com sucesso!', 'success')
    return redirect(url_for('atendimento_atual'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) as c FROM clientes')
    total = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) as c FROM atendimentos')
    atendidos = cur.fetchone()['c']
    
    cur.execute('''
        SELECT COUNT(*) as c FROM clientes c
        LEFT JOIN (
            SELECT cliente_id, MAX(id) as ultimo FROM atendimentos GROUP BY cliente_id
        ) a ON a.cliente_id = c.id
        WHERE a.ultimo IS NULL
    ''')
    espera = cur.fetchone()['c']

    avg_secs = average_wait_seconds()
    avg_min = round(avg_secs/60, 1) if avg_secs else None

    conn.close()
    return render_template('dashboard.html', total=total, atendidos=atendidos, espera=espera, avg_min=avg_min)

@app.route('/painel')
def painel_publico():
    return render_template('painel.html')

@app.route('/painel-next')
def painel_next():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT c.id, c.nome, c.telefone, c.created_at, c.servico_id
        FROM clientes c
        LEFT JOIN (
            SELECT cliente_id, MAX(id) as ultimo FROM atendimentos GROUP BY cliente_id
        ) a ON a.cliente_id = c.id
        WHERE a.ultimo IS NULL
    ''')
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return jsonify({'status': 'empty'})
    
    fila = build_fifo_queue(rows)
    
    if len(fila) == 0:
        return jsonify({'status': 'empty'})
    
    primeiro = fila.head
    return jsonify({'status': 'ok', 'cliente': {'id': primeiro.cliente_id, 'nome': primeiro.nome, 'telefone': primeiro.telefone}})

@app.route('/backup')
@login_required
def backup_db():
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{now}.db'
    shutil.copyfile(DB_PATH, backup_name)
    flash(f'Backup criado: {backup_name}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/report')
@login_required
def report():
    conn = get_conn()
    cur = conn.cursor()
    
    # Atendimentos por dia (apenas finalizados), com receita do dia
    cur.execute(
        '''
        SELECT date(saida) as dia, COUNT(*) as total, SUM(valor_pago) as receita
        FROM atendimentos
        WHERE saida IS NOT NULL
        GROUP BY dia
        ORDER BY dia DESC
        LIMIT 30
        '''
    )
    rows = cur.fetchall()
    
    # Totais agregados
    total_atendimentos = sum(row['total'] for row in rows) if rows else 0
    media_diaria = total_atendimentos / len(rows) if rows else 0
    
    cur.execute('''
        SELECT SUM(valor_pago) as receita_total, COUNT(*) as concluidos
        FROM atendimentos
        WHERE saida IS NOT NULL
    ''')
    agg = cur.fetchone()
    receita_total = float(agg['receita_total']) if agg and agg['receita_total'] is not None else 0.0
    concluidos = int(agg['concluidos']) if agg and agg['concluidos'] is not None else 0
    ticket_medio = (receita_total / concluidos) if concluidos else 0.0
    
    # Últimos atendimentos concluídos
    cur.execute('''
        SELECT a.id, c.nome, c.telefone, s.nome as servico, a.entrada, a.saida, a.tempo_atendimento, a.valor_pago
        FROM atendimentos a
        JOIN clientes c ON c.id = a.cliente_id
        LEFT JOIN servicos s ON s.id = a.servico_id
        WHERE a.saida IS NOT NULL
        ORDER BY a.saida DESC
        LIMIT 50
    ''')
    recentes = cur.fetchall()
    
    # Serviços mais populares
    cur.execute('''
        SELECT COALESCE(s.nome, 'Serviço') as nome, COUNT(*) as usos
        FROM atendimentos a
        LEFT JOIN servicos s ON s.id = a.servico_id
        WHERE a.saida IS NOT NULL
        GROUP BY s.nome
        ORDER BY usos DESC
        LIMIT 3
    ''')
    populares = cur.fetchall()
    
    conn.close()
    return render_template(
        'report.html',
        rows=rows,
        total_atendimentos=total_atendimentos,
        media_diaria=media_diaria,
        receita_total=receita_total,
        ticket_medio=ticket_medio,
        recentes=recentes,
        populares=populares,
    )

@app.route('/auto-registro', methods=['GET', 'POST'])
def auto_registro():
    """Página pública para clientes se registrarem na fila"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, nome, preco, duracao_estimada, descricao FROM servicos ORDER BY nome')
    servicos = cur.fetchall()
    conn.close()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        servico = request.form.get('servico')
        
        if not nome or not servico:
            flash('Nome e serviço são obrigatórios!', 'danger')
            return redirect(url_for('auto_registro'))
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO clientes (nome, telefone, servico_id) VALUES (?,?,?)',
                    (nome, telefone, servico))
        conn.commit()
        conn.close()
        
        flash('Você foi adicionado à fila! Aguarde ser chamado.', 'success')
        return redirect(url_for('painel_publico'))
    
    return render_template('auto_registro.html', servicos=servicos)

@app.route('/servicos')
@login_required
def list_servicos():
    """Lista todos os serviços do salão"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM servicos ORDER BY nome')
    servicos = cur.fetchall()
    conn.close()
    return render_template('servicos.html', servicos=servicos)

@app.route('/servicos/add', methods=['GET', 'POST'])
@login_required
def add_servico():
    """Adiciona novo serviço"""
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        preco = float(request.form['preco'])
        duracao = int(request.form.get('duracao_estimada', 30))
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO servicos (nome, descricao, preco, duracao_estimada) VALUES (?,?,?,?)',
                    (nome, descricao, preco, duracao))
        conn.commit()
        conn.close()
        
        flash('Serviço adicionado com sucesso!', 'success')
        return redirect(url_for('list_servicos'))
    
    return render_template('add_servico.html')

@app.route('/servicos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_servico(id):
    """Edita um serviço existente"""
    conn = get_conn()
    cur = conn.cursor()
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        preco = float(request.form['preco'])
        duracao = int(request.form.get('duracao_estimada', 30))
        
        cur.execute('UPDATE servicos SET nome=?, descricao=?, preco=?, duracao_estimada=? WHERE id=?',
                    (nome, descricao, preco, duracao, id))
        conn.commit()
        conn.close()
        
        flash('Serviço atualizado com sucesso!', 'success')
        return redirect(url_for('list_servicos'))
    
    cur.execute('SELECT * FROM servicos WHERE id = ?', (id,))
    servico = cur.fetchone()
    conn.close()
    
    return render_template('edit_servico.html', servico=servico)

@app.route('/atendimento/atual')
@login_required
def atendimento_atual():
    """Mostra clientes em atendimento"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.id, c.nome, c.telefone, s.nome as servico, s.preco,
               a.entrada, a.chamada
        FROM atendimentos a
        JOIN clientes c ON a.cliente_id = c.id
        LEFT JOIN servicos s ON a.servico_id = s.id
        WHERE a.saida IS NULL
        ORDER BY a.chamada DESC
    ''')
    atendimentos = cur.fetchall()
    conn.close()
    return render_template('atendimento_atual.html', atendimentos=atendimentos)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        from init_db import init_db
        init_db()
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug)
