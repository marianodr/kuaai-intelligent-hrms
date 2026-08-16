import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, Between } from 'typeorm';
import { AttendanceRecord } from '../attendance/entities/attendance-record.entity';
import { EmployeesService } from '../employees/employees.service';

/**
 * Fecha de referencia del dashboard. Si FAKE_TODAY_ENABLED=true, usa la
 * fecha fijada en FAKE_TODAY (ej. "2026-08-14") en vez de la real —
 * útil para QA/demos fuera de horario laboral. Desactivado por defecto.
 */
function getReferenceNow(): Date {
  const enabled = process.env.FAKE_TODAY_ENABLED === 'true';
  const fake = process.env.FAKE_TODAY;
  if (!enabled || !fake) return new Date();

  // "YYYY-MM-DD" a secas se parsea como medianoche UTC; con TZ=America/Argentina
  // eso cae en el día anterior local. Se fija al mediodía para evitar el corrimiento.
  return new Date(`${fake}T12:00:00`);
}

@Injectable()
export class DashboardService {
  constructor(
    @InjectRepository(AttendanceRecord)
    private readonly attendanceRepo: Repository<AttendanceRecord>,
    private readonly employeesService: EmployeesService,
  ) {}

  async getTodayAttendance() {
    const now = getReferenceNow();
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

  /** Días laborables transcurridos del mes y entradas (día, empleado) en ese rango. */
  private async getElapsedMonthData(month: number, year: number) {
    const daysInMonth = new Date(year, month, 0).getDate();
    const start = new Date(year, month - 1, 1);
    const monthEnd = new Date(year, month - 1, daysInMonth, 23, 59, 59);

    // Si el mes consultado es el actual, el rango solo llega hasta hoy
    // (no se puede esperar asistencia de días futuros).
    const now = getReferenceNow();
    const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1;
    const end = isCurrentMonth && now < monthEnd ? now : monthEnd;

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
      .getRawMany<{ day: string; employee_id: number }>();

    return { workdays, entries };
  }

  async getMonthlyAverage(month: number, year: number) {
    const activeEmployees = await this.employeesService.findActiveEmployees();
    const total = activeEmployees.length;
    if (total === 0) {
      return {
        month,
        year,
        workdays: 0,
        average_attendance_pct: 0,
        total_present: 0,
        total_expected: 0,
      };
    }

    const { workdays, entries } = await this.getElapsedMonthData(month, year);
    const totalExpected = total * workdays;
    const totalPresent = entries.length;
    const pct = totalExpected > 0 ? Math.round((totalPresent / totalExpected) * 100) : 0;

    return {
      month,
      year,
      workdays,
      average_attendance_pct: pct,
      total_present: totalPresent,
      total_expected: totalExpected,
    };
  }

  async getMonthlyAbsences(month: number, year: number) {
    const activeEmployees = await this.employeesService.findActiveEmployees();
    const { workdays, entries } = await this.getElapsedMonthData(month, year);

    const presentDaysByEmployee = new Map<number, number>();
    for (const e of entries) {
      presentDaysByEmployee.set(e.employee_id, (presentDaysByEmployee.get(e.employee_id) ?? 0) + 1);
    }

    const absences = activeEmployees
      .map((emp) => ({
        employee_id: emp.id,
        name: `${emp.first_name} ${emp.last_name}`,
        department: emp.department,
        count: workdays - (presentDaysByEmployee.get(emp.id) ?? 0),
      }))
      .filter((a) => a.count > 0)
      .sort((a, b) => b.count - a.count);

    return { month, year, workdays, absences };
  }

  async getRecentEntries(limit = 10) {
    const now = getReferenceNow();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);

    const records = await this.attendanceRepo.find({
      where: { record_type: 'ENTRADA', timestamp: Between(start, end) },
      relations: ['employee'],
      order: { timestamp: 'DESC' },
      take: limit,
    });

    return records.map((r) => ({
      id: r.id,
      employee_id: r.employee_id,
      name: `${r.employee.first_name} ${r.employee.last_name}`,
      department: r.employee.department,
      timestamp: r.timestamp,
      is_late: r.is_late,
    }));
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
