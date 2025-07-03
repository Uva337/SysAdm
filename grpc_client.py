"""Simple gRPC client for AdminMaster server."""
import grpc
from server.proto import adminmaster_pb2, adminmaster_grpc_pb2


def ping(server_addr: str = "localhost:50051") -> str:
    """Send Ping request to server and return message."""
    with grpc.insecure_channel(server_addr) as channel:
        stub = adminmaster_grpc_pb2.AdminMasterStub(channel)
        resp = stub.Ping(adminmaster_pb2.Empty())
        return resp.message


def list_servers(server_addr: str = "localhost:50051") -> list[str]:
    """Retrieve list of servers from server."""
    with grpc.insecure_channel(server_addr) as channel:
        stub = adminmaster_grpc_pb2.AdminMasterStub(channel)
        resp = stub.ListServers(adminmaster_pb2.Empty())
        return list(resp.names)


if __name__ == "__main__":
    print("Ping:", ping())
    print("Servers:", list_servers())
