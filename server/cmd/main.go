package main

import (
	"context"
	"log"
	"net"

	"google.golang.org/grpc"
	pb "server/proto"
)

type adminServer struct {
	pb.UnimplementedAdminMasterServer
}

func (s *adminServer) Ping(ctx context.Context, _ *pb.Empty) (*pb.Pong, error) {
	return &pb.Pong{Message: "pong"}, nil
}

func (s *adminServer) ListServers(ctx context.Context, _ *pb.Empty) (*pb.ServerList, error) {
	servers := []string{"srv-01", "srv-02"}
	return &pb.ServerList{Names: servers}, nil
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	pb.RegisterAdminMasterServer(grpcServer, &adminServer{})
	log.Println("gRPC server listening on :50051")
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("server exited: %v", err)
	}
}
