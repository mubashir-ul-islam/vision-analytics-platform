class AttendanceEvents {
  constructor() {
    this.handlers = [];
    this.source = null;
    this.reconnectDelay = 1000;
    this._stopped = false;
  }

  connect() {
    if (this._stopped) return;
    this.source = new EventSource("/api/events");

    this.source.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        this.handlers.forEach((h) => h(event));
      } catch (_) {}
    };

    this.source.onerror = () => {
      this.source.close();
      if (this._stopped) return;
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    };

    this.source.onopen = () => {
      this.reconnectDelay = 1000;
    };
  }

  subscribe(handler) {
    this.handlers.push(handler);
    return () => this.unsubscribe(handler);
  }

  unsubscribe(handler) {
    this.handlers = this.handlers.filter((h) => h !== handler);
  }

  disconnect() {
    this._stopped = true;
    this.source?.close();
  }
}

export const socket = new AttendanceEvents();
socket.connect();
