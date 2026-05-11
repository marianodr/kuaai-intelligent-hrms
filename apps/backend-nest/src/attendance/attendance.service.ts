import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, Between } from 'typeorm';
import { Cron, CronExpression } from '@nestjs/schedule';
import { AttendanceRecord, RecordType } from './entities/attendance-record.entity';
import { Employee } from '../employees/entities/employee.entity';
import { EmployeesService } from '../employees/employees.service';

// Hora límite para considerar tardanza: 08:15
const LATE_HOUR = 8;
const LATE_MINUTE = 15;

@Injectable()
export class AttendanceService {
  private readonly logger = new Logger(AttendanceService.name);

  constructor(
    @InjectRepository(AttendanceRecord)
    private readonly repo: Repository<AttendanceRecord>,
    private readonly employeesService: EmployeesService,
  ) {}

  async processRfidEvent(rfidCode: string): Promise<void> {
    const employee = await this.employeesService.findByRfid(rfidCode);
    if (!employee) {
      this.logger.warn(`RFID no reconocido o empleado inactivo: ${rfidCode}`);
      return;
    }

    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);

    const todayRecords = await this.repo.count({
      where: {
        employee_id: employee.id,
        timestamp: Between(todayStart, todayEnd),
        auto_generated: false,
      },
    });

    const recordType = this.determineRecordType(todayRecords);
    const isLate = recordType === 'ENTRADA' && this.isLate(now);

    const record = this.repo.create({
      employee_id: employee.id,
      timestamp: now,
      record_type: recordType,
      is_late: isLate,
      auto_generated: false,
    });

    await this.repo.save(record);
    this.logger.log(
      `Registro ${recordType} para ${employee.first_name} ${employee.last_name}` +
      (isLate ? ' [TARDANZA]' : ''),
    );
  }

  private determineRecordType(todayCount: number): RecordType {
    if (todayCount === 0) return 'ENTRADA';
    if (todayCount === 1) return 'SALIDA';
    return 'INTERMEDIO';
  }

  private isLate(date: Date): boolean {
    return (
      date.getHours() > LATE_HOUR ||
      (date.getHours() === LATE_HOUR && date.getMinutes() > LATE_MINUTE)
    );
  }

  // Cron diario a las 16:00 — genera salida automática a quien no la tenga
  @Cron('0 16 * * 1-5')
  async generateAutoExits(): Promise<void> {
    this.logger.log('Ejecutando cron de salida automática (16:00)');
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 15, 59, 59);

    const activeEmployees = await this.employeesService.findActiveEmployees();

    for (const employee of activeEmployees) {
      const hasEntry = await this.repo.findOne({
        where: {
          employee_id: employee.id,
          record_type: 'ENTRADA',
          timestamp: Between(todayStart, todayEnd),
        },
      });
      if (!hasEntry) continue;

      const hasExit = await this.repo.findOne({
        where: {
          employee_id: employee.id,
          record_type: 'SALIDA',
          timestamp: Between(todayStart, now),
        },
      });
      if (hasExit) continue;

      const autoRecord = this.repo.create({
        employee_id: employee.id,
        timestamp: now,
        record_type: 'SALIDA',
        is_late: false,
        auto_generated: true,
      });
      await this.repo.save(autoRecord);
      this.logger.log(`Salida automática generada para ${employee.first_name} ${employee.last_name}`);
    }
  }

  getRecordsByDateRange(employeeId: number, from: Date, to: Date) {
    return this.repo.find({
      where: { employee_id: employeeId, timestamp: Between(from, to) },
      order: { timestamp: 'ASC' },
    });
  }

  getTodayRecords() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
    return this.repo.find({
      where: { timestamp: Between(start, end) },
      relations: ['employee'],
      order: { timestamp: 'ASC' },
    });
  }
}
