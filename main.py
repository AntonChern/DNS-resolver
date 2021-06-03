import dns.query
import socket

time_to_live = 3600.

root_server = "198.41.0.4"

port = 53
ip = "127.0.0.1"

cache4 = dict()
cache6 = dict()

def refresh(cache, time):
    new_cache = dict()
    for note in cache.items():
        if note[1][0] > time:
            new_cache[note[0]] = note[1]
    return new_cache

def get_response(query):
    server_ip = root_server
    response = dns.query.udp(query, server_ip)
    while (not response.answer):
        server_record = None

        for record in response.additional:
            if record.rdtype == dns.rdatatype.A:
                server_record = record
                break

        if server_record is None:
            cur_servers = response.get_rrset(response.authority, query.question[0].name, dns.rdataclass.IN, dns.rdatatype.NS)
            if (cur_servers is None):
                break
            cur_query = dns.message.make_query(cur_servers[0].to_text(), dns.rdatatype.A)
            cur_response = dns.query.udp(cur_query, "8.8.4.4")
            for record in cur_response.answer:
                if record.rdtype == dns.rdatatype.A:
                    server_record = record
            if server_record is None:
                break
        server_ip = server_record[0].to_text()
        response = dns.query.udp(query, server_ip)
    return response

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))

    while True:
        query, cur_time, address = dns.query.receive_udp(sock)

        if query.question[0].rdtype == dns.rdatatype.A:
            cache = cache4
        if query.question[0].rdtype == dns.rdatatype.AAAA:
            cache = cache6
        domain = query.question[0].name.to_text()
        if cache.__contains__(domain) and cache[domain][0] > cur_time:
            r_time, response = cache[domain]
            new_response = dns.message.from_text(response)
            new_response.flags = dns.flags.QR | dns.flags.RD
            new_response.id = query.id
            new_response.answer[0].ttl = int(r_time - cur_time)
            cache[domain] = (r_time, new_response.to_text())
            dns.query.send_udp(sock, new_response, address)
        else:
            response = get_response(query)
            if response.answer:
                cache[domain] = (cur_time + time_to_live, response.to_text())
                dns.query.send_udp(sock, response, address)
        cache = refresh(cache, cur_time)