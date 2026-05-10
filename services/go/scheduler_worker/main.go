package main

import (
	"log"
	"os"
	"time"
)

func main() {
	interval := 15 * time.Second
	if env := os.Getenv("SCHEDULER_WORKER_SECONDS"); env != "" {
		if parsed, err := time.ParseDuration(env + "s"); err == nil {
			interval = parsed
		}
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	log.Printf("scheduler_worker started with interval %s", interval)
	for tick := range ticker.C {
		log.Printf("scheduler_worker heartbeat %s", tick.Format(time.RFC3339))
	}
}
