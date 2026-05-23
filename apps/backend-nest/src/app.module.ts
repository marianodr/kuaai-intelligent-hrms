import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ScheduleModule } from '@nestjs/schedule';

import { User } from './users/entities/user.entity';
import { Employee } from './employees/entities/employee.entity';
import { AttendanceRecord } from './attendance/entities/attendance-record.entity';

import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { EmployeesModule } from './employees/employees.module';
import { AttendanceModule } from './attendance/attendance.module';
import { DashboardModule } from './dashboard/dashboard.module';
import { MqttModule } from './mqtt/mqtt.module';
import { ProxyModule } from './proxy/proxy.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    ScheduleModule.forRoot(),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get('POSTGRES_HOST'),
        port: config.get<number>('POSTGRES_PORT'),
        database: config.get('POSTGRES_DB'),
        username: config.get('POSTGRES_USER'),
        password: config.get('POSTGRES_PASSWORD'),
        entities: [User, Employee, AttendanceRecord],
        synchronize: false,
      }),
    }),
    AuthModule,
    UsersModule,
    EmployeesModule,
    AttendanceModule,
    DashboardModule,
    MqttModule,
    ProxyModule,
  ],
})
export class AppModule {}
