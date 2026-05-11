import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, ILike } from 'typeorm';
import { Employee } from './entities/employee.entity';
import { CreateEmployeeDto } from './dto/create-employee.dto';
import { UpdateEmployeeDto } from './dto/update-employee.dto';

@Injectable()
export class EmployeesService {
  constructor(
    @InjectRepository(Employee) private readonly repo: Repository<Employee>,
  ) {}

  async findAll(page = 1, limit = 10, name?: string, department?: string) {
    const where: any = {};
    if (department) where.department = department;

    const qb = this.repo.createQueryBuilder('e');
    if (name) {
      qb.where(
        "(e.first_name ILIKE :name OR e.last_name ILIKE :name OR CONCAT(e.first_name,' ',e.last_name) ILIKE :name)",
        { name: `%${name}%` },
      );
    }
    if (department) qb.andWhere('e.department = :department', { department });

    const [data, total] = await qb
      .skip((page - 1) * limit)
      .take(limit)
      .orderBy('e.last_name', 'ASC')
      .getManyAndCount();

    return { data, total, page, limit, totalPages: Math.ceil(total / limit) };
  }

  async findOne(id: number): Promise<Employee> {
    const employee = await this.repo.findOne({ where: { id } });
    if (!employee) throw new NotFoundException(`Empleado #${id} no encontrado`);
    return employee;
  }

  findByRfid(rfid_code: string): Promise<Employee | null> {
    return this.repo.findOne({ where: { rfid_code, status: 'ACTIVO' } });
  }

  findActiveEmployees(): Promise<Employee[]> {
    return this.repo.find({ where: { status: 'ACTIVO' } });
  }

  create(dto: CreateEmployeeDto): Promise<Employee> {
    const employee = this.repo.create(dto);
    return this.repo.save(employee);
  }

  async update(id: number, dto: UpdateEmployeeDto): Promise<Employee> {
    const employee = await this.findOne(id);
    Object.assign(employee, dto);
    return this.repo.save(employee);
  }

  async deactivate(id: number): Promise<Employee> {
    const employee = await this.findOne(id);
    employee.status = 'INACTIVO';
    return this.repo.save(employee);
  }
}
