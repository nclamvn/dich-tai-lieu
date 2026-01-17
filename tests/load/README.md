# Load Testing with k6

This directory contains load testing scripts for AI Publisher Pro using [k6](https://k6.io/).

## Installation

### macOS
```bash
brew install k6
```

### Linux
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Windows
```powershell
choco install k6
```

## Test Scripts

| Script | Description | Use Case |
|--------|-------------|----------|
| `basic.js` | Basic API endpoint tests | Verify system works under normal load |
| `translation.js` | Full translation workflow | Test complete publishing pipeline |
| `websocket.js` | WebSocket connection tests | Test real-time update system |
| `stress.js` | Stress testing | Find breaking point |

## Running Tests

### Basic Load Test
```bash
k6 run tests/load/basic.js
```

### With Custom Base URL
```bash
k6 run -e BASE_URL=http://localhost:3001 tests/load/basic.js
```

### Translation Flow Test
```bash
k6 run tests/load/translation.js
```

### WebSocket Test
```bash
k6 run tests/load/websocket.js
```

### Stress Test
```bash
k6 run tests/load/stress.js
```

### With Custom Virtual Users
```bash
k6 run --vus 20 --duration 5m tests/load/basic.js
```

### Generate HTML Report
```bash
k6 run --out json=results.json tests/load/basic.js
# Then use k6-reporter or convert to HTML
```

## Test Scenarios

### Smoke Test
Verify the system works with minimal load.
```bash
k6 run -e TEST_TYPE=smoke tests/load/basic.js
```

### Load Test (Default)
Typical expected load.
```bash
k6 run tests/load/basic.js
```

### Stress Test
Find the breaking point.
```bash
k6 run tests/load/stress.js
```

### Spike Test
Sudden traffic increase.
```bash
k6 run --stage 1m:5 --stage 10s:100 --stage 1m:100 --stage 10s:5 tests/load/basic.js
```

### Soak Test
Extended duration to find memory leaks.
```bash
k6 run --stage 2m:20 --stage 30m:20 --stage 2m:0 tests/load/basic.js
```

## Interpreting Results

### Key Metrics
- `http_req_duration`: Response time
- `http_req_failed`: Failed request rate
- `http_reqs`: Total requests per second
- `vus`: Virtual users
- `iterations`: Completed test iterations

### Thresholds
The tests are configured with the following thresholds:
- 95% of requests should complete within 500ms
- Error rate should be below 1%
- Health check should respond within 100ms

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Load Tests
on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start server
        run: |
          docker-compose up -d
          sleep 10

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Run load tests
        run: k6 run tests/load/basic.js

      - name: Stop server
        run: docker-compose down
```

## Configuration

Edit `k6.config.js` to modify:
- Base URL
- Thresholds
- Stage configurations
- Custom tags

## Troubleshooting

### Connection Refused
Make sure the server is running:
```bash
curl http://localhost:3001/health
```

### High Error Rate
- Check server logs for errors
- Reduce virtual users
- Increase timeouts

### WebSocket Issues
- Verify WebSocket endpoint is enabled
- Check for proxy/firewall blocking WS connections
