# simulation_core.py

import threading
import time
import random
from datetime import datetime
import networkx as nx

# --- Global State ---
simulation_state = {
    'running': False,
    'handler_frames': ['(Empty)', '(Empty)', '(Empty)', '(Empty)'],
    'resources': ['Free', 'Free', 'Free', 'Free'],
    'waiting_queue': [],
    'log': ['System initialized.'],
    'utilization': 0,
    'resource_labels': ["DB Connection", "Media Service", "Notification Service", "Message Queue"]
}

simulation_lock = threading.Lock()
simulation_thread = None
user_counter = 0
MAX_TOTAL_USERS = 50
user_info = {} # Maps user name -> info dict

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    simulation_state['log'].append(f"[{timestamp}] {message}")



def create_user(name):
    needed_resources = random.sample(range(4), random.randint(1, 4))
    return {
        'resources_needed': needed_resources,
        'current_resource_index': 0,
        'held_resources': set(),
        'execution_time': 0,
        'timer': 0,
        'state': 'acquiring'
    }

def detect_deadlock_with_nx():
    wait_for_graph = nx.DiGraph()
    for p in user_info.keys():
        wait_for_graph.add_node(p)
    
    for proc, info in user_info.items():
        if info['current_resource_index'] < len(info['resources_needed']):
            waiting_resource_index = info['resources_needed'][info['current_resource_index']]
            holder = simulation_state['resources'][waiting_resource_index]
            
            if holder != 'Free' and holder != proc and holder in user_info:
                wait_for_graph.add_edge(proc, holder)

    return list(nx.simple_cycles(wait_for_graph))

def simulation_loop():
    global user_counter
    while True:
        with simulation_lock:
            if not simulation_state['running']:
                break
            
            #  ADD NEW USERS 
            if user_counter < MAX_TOTAL_USERS and random.random() < 0.6 and len(simulation_state['waiting_queue']) < 8:
                user_counter += 1
                new_proc = f"User{user_counter}"
                user_info[new_proc] = create_user(new_proc)
                simulation_state['waiting_queue'].append(new_proc)

            #  LOAD USERS INTO HANDLERS 
            for i, slot in enumerate(simulation_state['handler_frames']):
                if slot == '(Empty)' and simulation_state['waiting_queue']:
                    next_proc = simulation_state['waiting_queue'].pop(0)
                    simulation_state['handler_frames'][i] = next_proc
                    user_info[next_proc]['state'] = 'running'

            #  EXECUTE USERS (Acquire/Release Resources) 
            next_handler_frames = list(simulation_state['handler_frames'])
            
            for i, proc in enumerate(simulation_state['handler_frames']):
                if proc == '(Empty)' or proc not in user_info:
                    continue
                
                info = user_info[proc]
                
                if info['state'] == 'finished':
                    log_event(f"{proc} finished executing.")
                    for r in list(info['held_resources']):
                        if simulation_state['resources'][r] == proc:
                            simulation_state['resources'][r] = 'Free'
                            log_event(f"{proc} released {simulation_state['resource_labels'][r]}")
                    del user_info[proc]
                    next_handler_frames[i] = '(Empty)'
                    continue

                if info['state'] == 'running':
                    if info['timer'] > 0:
                        info['timer'] -= 1
                        continue
                        
                    cr_idx = info['current_resource_index']
                    if cr_idx < len(info['resources_needed']):
                        r_needed = info['resources_needed'][cr_idx]
                        
                        if simulation_state['resources'][r_needed] == 'Free':
                            simulation_state['resources'][r_needed] = proc
                            info['held_resources'].add(r_needed)
                            info['current_resource_index'] += 1
                            log_event(f"{proc} allocated {simulation_state['resource_labels'][r_needed]}")
                            info['timer'] = random.randint(3, 8)
                            
                            if info['current_resource_index'] == len(info['resources_needed']):
                                info['state'] = 'finished'
                        else:
                            info['state'] = 'blocked'
                            simulation_state['waiting_queue'].append(proc)
                            next_handler_frames[i] = '(Empty)'
            
            simulation_state['handler_frames'] = next_handler_frames

            #  DEADLOCK DETECTION & RESOLUTION 
            deadlocks = detect_deadlock_with_nx()
            
            if deadlocks:
                log_event(f"Deadlock detected! Cycles: {deadlocks}")
                for cycle in deadlocks:
                    proc_to_kill = cycle[0]
                    if proc_to_kill in user_info:
                        log_event(f"{proc_to_kill} Terminated to resolve deadlock.")
                        for r in list(user_info[proc_to_kill]['held_resources']):
                            if simulation_state['resources'][r] == proc_to_kill:
                                simulation_state['resources'][r] = 'Free'

                        if proc_to_kill in simulation_state['waiting_queue']:
                            simulation_state['waiting_queue'].remove(proc_to_kill)
                        try:
                            handler_index = simulation_state['handler_frames'].index(proc_to_kill)
                            simulation_state['handler_frames'][handler_index] = '(Empty)'
                        except ValueError:
                            pass
                        
                        del user_info[proc_to_kill]

            #  UPDATE UTILIZATION 
            active_procs = sum(1 for proc in simulation_state['handler_frames'] if proc != '(Empty)')
            total_slots = len(simulation_state['handler_frames'])
            simulation_state['utilization'] = int((active_procs / total_slots) * 100) if total_slots > 0 else 0

            #  MANAGE LOG SIZE 
            if len(simulation_state['log']) > 50:
                simulation_state['log'] = simulation_state['log'][-50:]
        
        time.sleep(1)

# --- Functions for app.py to call ---

def start_simulation():
    global simulation_thread
    with simulation_lock:
        if not simulation_state['running']:
            simulation_state['running'] = True
            if simulation_thread is None or not simulation_thread.is_alive():
                simulation_thread = threading.Thread(target=simulation_loop)
                simulation_thread.start()
            log_event('Simulation started.')
            return {'status': 'started'}
        return {'status': 'already running'}

def pause_simulation():
    with simulation_lock:
        simulation_state['running'] = False
        return {'status': 'paused'}

def resume_simulation():
    global simulation_thread
    with simulation_lock:
        if not simulation_state['running']:
            simulation_state['running'] = True
            if simulation_thread is None or not simulation_thread.is_alive():
                simulation_thread = threading.Thread(target=simulation_loop)
                simulation_thread.start()
            return {'status': 'resumed'}
        return {'status': 'already running'}

def stop_simulation():
    with simulation_lock:
        simulation_state['running'] = False
        log_event('Simulation stopped.')
        return {'status': 'stopped'}

def get_simulation_state():
    with simulation_lock:
        # Create a display-friendly version of the state
        handler_display = [f"{proc} [{user_info.get(proc, {}).get('state', 'unknown')}]" if proc != '(Empty)' else '(Empty)' for proc in simulation_state['handler_frames']]
        waiting_display = [proc for proc in simulation_state['waiting_queue']]
        
        state_copy = simulation_state.copy()
        state_copy['handler_frames'] = handler_display
        state_copy['waiting_queue'] = waiting_display
        return state_copy

def get_wait_for_graph_data():
    with simulation_lock:
        nodes = []
        edges = []

        deadlocks = detect_deadlock_with_nx()
        deadlocked_nodes = set(node for cycle in deadlocks for node in cycle)

        for proc in user_info.keys():
            is_deadlocked = proc in deadlocked_nodes
            nodes.append({'id': proc, 'label': f"{proc}\n({user_info[proc]['state']})", 'type': 'user', 'is_deadlocked': is_deadlocked})

        for proc, info in user_info.items():
            if info['current_resource_index'] < len(info['resources_needed']):
                waiting_resource_index = info['resources_needed'][info['current_resource_index']]
                holder = simulation_state['resources'][waiting_resource_index]
                
                if holder != 'Free' and holder in user_info and holder != proc:
                    edges.append({'from': proc, 'to': holder, 'arrows': 'to', 'label': f"waits for {simulation_state['resource_labels'][waiting_resource_index]}"})

        return {'nodes': nodes, 'edges': edges}