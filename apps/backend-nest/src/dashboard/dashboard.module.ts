import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AttendanceRecord } from '../attendance/entities/attendance-record.entity';
import { DashboardService } from './dashboard.service';
import { DashboardController } from './dashboard.controller';
import { EmployeesModule } from '../employees/employees.module';

@Module({
  imports: [TypeOrmModule.forFeature([AttendanceRecord]), EmployeesModule],
  providers: [DashboardService],
  controllers: [DashboardController],
})
export class DashboardModule {}
