class Node:
    """
    Nó da lista encadeada representando um cliente na fila do salão
    """
    def __init__(self, cliente_id, nome, telefone, servico_id, created_at):
        self.cliente_id = cliente_id
        self.nome = nome
        self.telefone = telefone
        self.servico_id = servico_id
        self.created_at = created_at
        self.next = None

class LinkedList:
    """
    Lista encadeada para gerenciar a fila de clientes do salão
    Sistema FIFO (First In, First Out) - o primeiro a chegar é o primeiro a ser atendido
    """
    def __init__(self):
        self.head = None
    
    def __len__(self):
        count = 0
        current = self.head
        while current:
            count += 1
            current = current.next
        return count

    def append(self, cliente_id, nome, telefone, servico_id, created_at):
        """Adiciona um cliente ao final da fila"""
        new_node = Node(cliente_id, nome, telefone, servico_id, created_at)
        if not self.head:
            self.head = new_node
            return
        last = self.head
        while last.next:
            last = last.next
        last.next = new_node

    def remove_head(self):
        """Remove e retorna o primeiro cliente da fila (FIFO)"""
        if not self.head:
            return None
        removed_node = self.head
        self.head = self.head.next
        return removed_node
    
    def get_all(self):
        """Retorna todos os clientes da fila como lista"""
        result = []
        current = self.head
        while current:
            result.append({
                'cliente_id': current.cliente_id,
                'nome': current.nome,
                'telefone': current.telefone,
                'servico_id': current.servico_id,
                'created_at': current.created_at
            })
            current = current.next
        return result

class FIFOSort:
    """
    Classe para ordenar a fila por ordem de chegada (FIFO)
    Não há prioridade - todos são atendidos na ordem de chegada
    """
    @staticmethod
    def sort_linked_list(linked_list):
        """
        Ordena a lista pela data de criação (created_at)
        O cliente que chegou primeiro será atendido primeiro
        """
        if not linked_list.head:
            return linked_list

        # Converter para lista para ordenar por created_at
        nodes = []
        current = linked_list.head
        while current:
            nodes.append(current)
            next_node = current.next
            current.next = None
            current = next_node
        
        # Ordenar por created_at (ordem crescente - mais antigo primeiro)
        nodes.sort(key=lambda x: x.created_at)
        
        # Recriar a lista encadeada na ordem correta
        sorted_list = LinkedList()
        for node in nodes:
            sorted_list.append(
                node.cliente_id,
                node.nome,
                node.telefone,
                node.servico_id,
                node.created_at
            )
        
        return sorted_list