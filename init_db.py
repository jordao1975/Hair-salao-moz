from flask import g
import sqlite3

DB_PATH = 'clientes_hair_salon.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    with conn:
        # Tabela de usuários (funcionários)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        
        # Tabela de serviços do salão
        conn.execute('''
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                preco REAL NOT NULL,
                duracao_estimada INTEGER
            )
        ''')
        
        # Tabela de clientes
        conn.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                servico_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (servico_id) REFERENCES servicos (id)
            )
        ''')
        
        # Tabela de atendimentos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS atendimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                servico_id INTEGER,
                entrada TEXT NOT NULL,
                chamada TEXT,
                saida TEXT,
                tempo_atendimento INTEGER,
                valor_pago REAL,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                FOREIGN KEY (servico_id) REFERENCES servicos (id)
            )
        ''')
        
        # Inserir usuário padrão (admin/admin123)
        conn.execute('''
            INSERT OR IGNORE INTO usuarios (username, password, role)
            VALUES ('admin', 'admin123', 'admin')
        ''')
        
        # Inserir serviços padrão do salão moçambicano
        servicos_padrao = [
            ('Corte de Cabelo Masculino', 'Corte tradicional ou moderno', 150.00, 30),
            ('Corte de Cabelo Feminino', 'Corte e acabamento', 200.00, 45),
            ('Barba', 'Aparar e modelar barba', 100.00, 20),
            ('Corte + Barba', 'Combo completo', 220.00, 45),
            ('Tranças', 'Diversos estilos de tranças', 300.00, 90),
            ('Penteado', 'Penteado para eventos', 250.00, 60),
            ('Coloração', 'Tingir cabelo', 400.00, 90),
            ('Alisamento', 'Tratamento alisante', 500.00, 120),
            ('Hidratação', 'Tratamento capilar', 200.00, 45),
            ('Manicure', 'Tratamento de unhas das mãos', 100.00, 30),
            ('Pedicure', 'Tratamento de unhas dos pés', 150.00, 45)
        ]
        
        for servico in servicos_padrao:
            conn.execute('''
                INSERT OR IGNORE INTO servicos (nome, descricao, preco, duracao_estimada)
                VALUES (?, ?, ?, ?)
            ''', servico)
    
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Base de dados inicializada com sucesso!')