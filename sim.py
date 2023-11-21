# %% [markdown]
# 

# %%
#gerado com apoio do chatGPT
import heapq
import random
import math
from enum import Enum
from typing import List, Union

# %% [markdown]
# ## ENUMS

# %%
class EVENTOS(Enum):
    CHEGADA = "Chegada"
    PARTIDA = "Partida"
    SERVICE = "Service"

# %% [markdown]
# ## Classe geradora de números randômicos

# %%
class LCG:
    def __init__(self, seed, a, c, m):
        """
        Inicializa o gerador LCG com os parâmetros fornecidos.

        Args:
            seed: Semente inicial para o gerador.
            a: Coeficiente multiplicativo.
            c: Coeficiente aditivo.
            m: Módulo.
        """
        self.seed = seed
        self.a = a
        self.c = c
        self.m = m

    def sample(self):
        """
        Amostra um valor da sequência de números pseudoaleatórios.

        Returns:
            Um número pseudoaleatório.
        """
        self.seed = (self.a * self.seed + self.c) % self.m
        return self.seed / self.m  # Normaliza o valor para estar entre 0 e 1

# %% [markdown]
# ## Classe Queue de eventos

# %%
class Queue:
    def __init__(self):
        self.buffer = []  # Buffer para armazenar os eventos

    def enqueue(self, event):
        heapq.heappush(self.buffer, event)

    def dequeue(self):
        return heapq.heappop(self.buffer)

    def is_empty(self):
        return len(self.buffer) == 0
    
    def size(self):
        return len(self.buffer)

# %% [markdown]
# ## Classe para representar o evento

# %%
class Event:
    def __init__(self, time, action, event_type, mm1, client_id):
        self.time = time
        self.action = action
        self.event_type = event_type
        self.mm1 = mm1
        self.client_id = client_id

    def __lt__(self, other):
        return self.time < other.time
    
    def __repr__(self) -> str:
        if self.event_type in(EVENTOS.PARTIDA, EVENTOS.CHEGADA):
            return f"{self.time:.2f} - {self.mm1.name} - {self.event_type.value} do Cliente {self.client_id:07d}"
        else:
            return ""

# %% [markdown]
# ## Classe MM1
# 

# %%
class MM1:
    def __init__(self, name, arrival_rate, service_rate, queue_size, simulator) -> None:
        self.name = name
        self.simulator = simulator
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.num_customers_served_from_queue = 0
        self.num_drop = 0
        self.queue_size = queue_size
        self.queue_waiting_time = 0
        self.idle = True
        self.queue = Queue()
        self.cin = None
        self.cout = None

        self.LCG = LCG(12345, 1103515245, 12345, 2**31)

    def __repr__(self) -> str:
        return f"{self.name} with ar = {self.arrival_rate} and sr = {self.service_rate}"

    def exponential_random_variate(self, rate):
        # return -math.log(1.0 - random.random()) / rate
        time = -math.log(1.0 - self.LCG.sample()) / rate
        # print(time)
        return time

    def arrival_action(self, client_id):
        if self.idle == True:
            service_time = self.exponential_random_variate(self.service_rate)
            self.simulator.response_time += service_time
            self.simulator.schedule_event(
                service_time, lambda: self.departure_action(client_id), EVENTOS.PARTIDA, self, client_id
            )
            self.idle = False
            # print("Inicia serviço")
        else:
            # Adiciona o evento à fila com o tempo de chegada
            if self.queue.size() <= self.queue_size:
                event = Event(self.simulator.current_time, None, EVENTOS.CHEGADA, self, client_id)
                # print("Enfileira")
                self.queue.enqueue(event)
            else:
                pass
                # print("Dropped")

        if self.name == "rec":
            interarrival_time = self.exponential_random_variate(self.arrival_rate)
            new_client = client_id + 1
            evento = EVENTOS.CHEGADA
            self.simulator.schedule_event(
                interarrival_time, lambda: self.arrival_action(new_client), evento, self, new_client
            )

    def departure_action(self, client_id):
        self.simulator.num_customers_served += 1
        service_time = 0
        if not self.queue.is_empty():
            event = self.queue.dequeue()
            client_id = event.client_id
            waiting_time = self.simulator.current_time - event.time
            self.queue_waiting_time += waiting_time
            # print("Tempo {:.2f}: Tempo espera de cliente".format(self.queue_waiting_time))
            self.num_customers_served_from_queue += 1
            service_time = self.exponential_random_variate(self.service_rate)
            self.simulator.response_time += waiting_time + service_time
            # Proximo departure
            self.simulator.schedule_event(
                service_time, lambda: self.departure_action(client_id), EVENTOS.PARTIDA, self, client_id
            )
        else:
            self.idle = True

        if not self.cout is None:
            mm1_next = self.cout.next()
            self.simulator.schedule_event(
                service_time,
                lambda: mm1_next.arrival_action(client_id),
                EVENTOS.CHEGADA,
                mm1_next,
                client_id,
            )

# %% [markdown]
# ## Classe Connector

# %%
class Connector:
    def __init__(self, IN: List[MM1], OUT: List[MM1], prob_out: List[int]):
        self.IN = IN
        self.OUT = OUT

        if sum(prob_out) == 1:
            self.prob_send = prob_out
        else:
            return None

        for i in self.IN:
            i.cout = self

        for o in self.OUT:
            o.cin = self

    def __repr__(self) -> str:
        enter = ", ".join([i.name for i in self.IN])
        leave = ", ".join([o.name for o in self.OUT])
        return f"Connecting {enter} to {leave}"

    def next(self) -> Union[MM1, None]:
        if self.OUT:
            # FIXME Gerar uma resposta com base nas probabilidades de cada saida
            return self.OUT[0]
        else:
            return None

# %% [markdown]
# ## Classe para o simulador

# %%
class Simulator:
    def __init__(self):
        self.current_time = 0
        self.event_queue = []
        self.server_idle = True
        self.num_customers_served = 0
        self.response_time = 0  # Armazena a acumulado o tempo de TEMPO ESPERA no Sistema        

        self.recepcao = MM1("rec", 0.5, 1, 5, self)
        self.triagem = MM1("    ate", 0.5, 1, 5, self)
        self.atendimento = MM1("        pag", 0.5, 1, 5, self)
        self.rec_tri = Connector([self.recepcao], [self.triagem], [1])
        self.tri_ate = Connector([self.triagem], [self.atendimento], [1])
        self.LCG = LCG(12345, 1103515245, 12345, 2**31)

    def schedule_event(self, delay, action, event_type, mm1, client_id):
        event_time = self.current_time + delay
        event = Event(event_time, action, event_type, mm1, client_id)
        heapq.heappush(self.event_queue, event)

    def exponential_random_variate(self, rate):
        # return -math.log(1.0 - random.random()) / rate
        time = -math.log(1.0 - self.LCG.sample()) / rate
        # print(time)
        return time    

    def run(self, end_time):
        client_id = 1
        self.schedule_event(
            0, lambda: self.recepcao.arrival_action(client_id), EVENTOS.CHEGADA, self.recepcao, client_id
        )

        while self.current_time < end_time:
            if not self.event_queue:
                break

            event = heapq.heappop(self.event_queue)
            print(event)
            self.current_time = event.time

            event.action()
        # print(
        #     "Tempo {:.2f}: Número médio de requisições no sistema no Sistema".format(
        #         self.response_time / self.current_time
        #     )
        # )
        print("Tempo {:.2f}: Total Requisicoes no Sistema".format(self.num_customers_served))
        print("Tempo {:.2f}: Vazao no Sistema".format(self.num_customers_served / end_time))
        # print("Tempo {:.2f}: Tempo Resposta Medio no Sistema".format(self.response_time / self.num_customers_served))

# %% [markdown]
# ## Iniciando simulação

# %%
simulation_time = 20000  # Tempo total de simulação

simulator = Simulator()
simulator.run(simulation_time)

# %% [markdown]
# 


