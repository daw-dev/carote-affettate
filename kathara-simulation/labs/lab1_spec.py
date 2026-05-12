N_HOST = 4
N_SWITCH = 4

def host_connections(host_id):
    return [f"S{host_id}"]

switch_connections_array = [
    ["A", "D", "F"],
    ["A", "B", "E"],
    ["B", "C", "F"],
    ["C", "D", "E"],
]

def switch_connections(switch_id: int) -> list[str]:
    return [f"S{switch_id}", *switch_connections_array[switch_id]]

def link_capacity(link_id: str):
    match link_id:
        case "A": return 20
        case "B": return 5
        case "C": return 10
        case "D": return 5
        case "E": return 7
        case "F": return 10
        case _: return -1
