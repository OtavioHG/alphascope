package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
)

type HealthResponse struct {
	Service string `json:"service"`
	Status  string `json:"status"`
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(HealthResponse{Service: "ingestion_service", Status: "ok"})
}

func main() {
	addr := ":8081"
	if env := os.Getenv("INGESTION_SERVICE_ADDR"); env != "" {
		addr = env
	}
	http.HandleFunc("/health", healthHandler)
	log.Printf("ingestion_service listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}
