import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { DataSource } from 'typeorm';

@Injectable()
export class CleanupService {
  private readonly logger = new Logger(CleanupService.name);

  constructor(private readonly dataSource: DataSource) {}

  @Cron(CronExpression.EVERY_DAY_AT_3AM)
  async cleanupStaleThreads(): Promise<void> {
    const result = await this.dataSource.query(`
      DELETE FROM conversation_threads
      WHERE last_message_at < NOW() - INTERVAL '30 days'
    `);
    const count = result[1] ?? 0;
    if (count > 0) {
      this.logger.log(`Cleanup: eliminados ${count} hilos inactivos (>30 días)`);
    }
  }
}
