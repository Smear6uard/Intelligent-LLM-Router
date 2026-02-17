#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Starting Intelligent LLM Router...${NC}"

# Cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start backend
echo -e "${BLUE}Starting backend on :8000...${NC}"
cd "$(dirname "$0")/backend"
pip install -q -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo -e "${BLUE}Starting frontend on :5173...${NC}"
cd "$(dirname "$0")/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!

echo -e "\n${GREEN}Ready!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:5173"
echo -e "  API docs: http://localhost:8000/docs"
echo ""

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID
