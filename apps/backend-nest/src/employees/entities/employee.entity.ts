import {
  Entity, PrimaryGeneratedColumn, Column,
  CreateDateColumn, UpdateDateColumn, OneToMany,
} from 'typeorm';
import { AttendanceRecord } from '../../attendance/entities/attendance-record.entity';

export type EmployeeStatus = 'ACTIVO' | 'INACTIVO';

@Entity('employees')
export class Employee {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ length: 100 })
  first_name: string;

  @Column({ length: 100 })
  last_name: string;

  @Column({ unique: true, nullable: true })
  email: string;

  @Column({ unique: true, length: 50 })
  legajo: string;

  @Column({ unique: true, length: 100 })
  rfid_code: string;

  @Column({ nullable: true })
  department: string;

  @Column({ type: 'varchar', length: 20, default: 'ACTIVO' })
  status: EmployeeStatus;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;

  @OneToMany(() => AttendanceRecord, (record) => record.employee)
  attendance_records: AttendanceRecord[];
}
