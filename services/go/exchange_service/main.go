package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
)

type ExchangeStatus struct {
	Service  string `json:"service"`
	Exchange string `json:"exchange"`
	Status   string `json:"status"`
}

func statusHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(ExchangeStatus{Service: "exchange_service", Exchange: "binance", Status: "ready"})
}

func main() {
	addr := ":8082"
	if env := os.Getenv("EXCHANGE_SERVICE_ADDR"); env != "" {
		addr = env
	}
	http.HandleFunc("/status", statusHandler)
	log.Printf("exchange_service listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}
