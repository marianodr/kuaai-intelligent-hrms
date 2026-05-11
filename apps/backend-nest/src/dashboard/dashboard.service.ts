import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, Between } from 'typeorm';
import { AttendanceRecord } from '../attendance/entities/attendance-record.entity';
import { EmployeesService } from '../employees/employees.service';

@Injectable()
export class DashboardService {
  constructor(
    @InjectRepository(AttendanceRecord)
    private readonly attendanceRepo: Repository<AttendanceRecord>,
    private readonly employeesService: EmployeesService,
  ) {}

  async getTodayAttendance() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);

    const activeEmployees = await this.employeesService.findActiveEmployees();
    const total = activeEmployees.length;

    const presentIds = new Set(
      (await this.attendanceRepo.find({
        where: { record_type: 'ENTRADA', timestamp: Between(start, end) },
        select: ['employee_id'],
      })).map((r) => r.employee_id),
    );

    const present = presentIds.size;
    const absentEmployees = activeEmployees.filter((e) => !presentIds.has(e.id));

    return {
      date: now.toISOString().split('T')[0],
      total_active: total,
      present,
      absent: total - present,
      attendance_pct: total > 0 ? Math.round((present / total) * 100) : 0,
      absent_employees: absentEmployees.map((e) => ({
        id: e.id,
        name: `${e.first_name} ${e.last_name}`,
        department: e.department,
      })),
    };
  }

  async getMonthlyAverage(month: number, year: number) {
    const daysInMonth = new Date(year, month, 0).getDate();
    const start = new Date(year, month - 1, 1);
    const end = new Date(year, month - 1, daysInMonth, 23, 59, 59);

    const activeEmployees = await this.employeesService.findActiveEmployees();
    const total = activeEmployees.length;
    if (total === 0) return { month, year, average_attendance_pct: 0 };

    // Días laborables (lun-vie) del mes
    let workdays = 0;
    const cursor = new Date(start);
    while (cursor <= end) {
      const day = cursor.getDay();
      if (day !== 0 && day !== 6) workdays++;
      cursor.setDate(cursor.getDate() + 1);
    }

    const entries = await this.attendanceRepo
      .createQueryBuilder('a')
      .select("DATE_TRUNC('day', a.timestamp)", 'day')
      .addSelect('a.employee_id', 'employee_id')
      .where('a.record_type = :type', { type: 'ENTRADA' })
      .andWhere('a.timestamp BETWEEN :start AND :end', { start, end })
      .groupBy('day, a.employee_id')
      .getRawMany();

    const totalExpected = total * workdays;
    const totalPresent = entries.length;
    const pct = totalExpected > 0 ? Math.round((totalPresent / totalExpected) * 100) : 0;

    return { month, year, workdays, average_attendance_pct: pct };
  }

  async getTardinessReport(month: number, year: number) {
    const daysInMonth = new Date(year, month, 0).getDate();
    const start = new Date(year, month - 1, 1);
    const end = new Date(year, month - 1, daysInMonth, 23, 59, 59);

    const lateRecords = await this.attendanceRepo.find({
      where: { is_late: true, timestamp: Between(start, end) },
      relations: ['employee'],
    });

    const byEmployee = new Map<number, { name: string; department: string; count: number }>();
    for (const r of lateRecords) {
      const key = r.employee_id;
      if (!byEmployee.has(key)) {
        byEmployee.set(key, {
          name: `${r.employee.first_name} ${r.employee.last_name}`,
          department: r.employee.department,
          count: 0,
        });
      }
      byEmployee.get(key).count++;
    }

    return {
      month,
      year,
      tardiness: Array.from(byEmployee.entries())
        .map(([id, data]) => ({ employee_id: id, ...data }))
        .sort((a, b) => b.count - a.count),
    };
  }
}
