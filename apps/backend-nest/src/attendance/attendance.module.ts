import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AttendanceRecord } from './entities/attendance-record.entity';
import { AttendanceService } from './attendance.service';
import { EmployeesModule } from '../employees/employees.module';

@Module({
  imports: [TypeOrmModule.forFeature([AttendanceRecord]), EmployeesModule],
  providers: [AttendanceService],
  exports: [AttendanceService],
})
export class AttendanceModule {}
