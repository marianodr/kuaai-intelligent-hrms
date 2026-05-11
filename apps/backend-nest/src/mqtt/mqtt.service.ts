import { Injectable, OnModuleInit, OnModuleDestroy, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as mqtt from 'mqtt';
import { AttendanceService } from '../attendance/attendance.service';

@Injectable()
export class MqttService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(MqttService.name);
  private client: mqtt.MqttClient;

  constructor(
    private readonly config: ConfigService,
    private readonly attendanceService: AttendanceService,
  ) {}

  onModuleInit() {
    const host = this.config.get<string>('MQTT_HOST', 'localhost');
    const port = this.config.get<number>('MQTT_PORT', 1883);
    const topic = this.config.get<string>('MQTT_TOPIC_ATTENDANCE', 'attendance/checkin');

    this.client = mqtt.connect(`mqtt://${host}:${port}`, {
      reconnectPeriod: 5000,
      connectTimeout: 10000,
    });

    this.client.on('connect', () => {
      this.logger.log(`Conectado a MQTT broker ${host}:${port}`);
      this.client.subscribe(topic, (err) => {
        if (err) this.logger.error(`Error suscribiendo a ${topic}: ${err.message}`);
        else this.logger.log(`Suscripto a topic: ${topic}`);
      });
    });

    this.client.on('message', async (receivedTopic, message) => {
      try {
        const payload = JSON.parse(message.toString());
        if (!payload?.rfid_code) {
          this.logger.warn(`Payload MQTT inválido en ${receivedTopic}`);
          return;
        }
        await this.attendanceService.processRfidEvent(payload.rfid_code);
      } catch (err) {
        this.logger.error(`Error procesando mensaje MQTT: ${err.message}`);
      }
    });

    this.client.on('error', (err) => {
      this.logger.error(`Error MQTT: ${err.message}`);
    });

    this.client.on('reconnect', () => {
      this.logger.warn('Reconectando a MQTT broker...');
    });
  }

  onModuleDestroy() {
    this.client?.end();
  }
}
