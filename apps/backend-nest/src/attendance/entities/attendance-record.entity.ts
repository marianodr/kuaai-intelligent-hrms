import {
  Entity, PrimaryGeneratedColumn, Column,
  CreateDateColumn, ManyToOne, JoinColumn,
} from 'typeorm';
import { Employee } from '../../employees/entities/employee.entity';

export type RecordType = 'ENTRADA' | 'SALIDA' | 'INTERMEDIO';

@Entity('attendance_records')
export class AttendanceRecord {
  @PrimaryGeneratedColumn()
  id: number;

  @ManyToOne(() => Employee, (employee) => employee.attendance_records)
  @JoinColumn({ name: 'employee_id' })
  employee: Employee;

  @Column()
  employee_id: number;

  @Column({ type: 'timestamp' })
  timestamp: Date;

  @Column({ type: 'varchar', length: 20 })
  record_type: RecordType;

  @Column({ default: false })
  is_late: boolean;

  @Column({ default: false })
  auto_generated: boolean;

  @CreateDateColumn()
  created_at: Date;
}
